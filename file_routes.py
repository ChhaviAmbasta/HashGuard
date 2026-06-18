"""
HashGuard - Secure File Storage Routes
Path: file_routes.py
Purpose: Flask blueprint for authenticated file upload, global repository listing,
         download, integrity verification, owner-only delete, and file detail views.
"""

import os

from flask import Blueprint, flash, redirect, render_template, request, send_file, session, url_for

from file_service import (
    format_file_size,
    get_file_absolute_path,
    get_file_audit_logs,
    get_file_by_id,
    get_owned_file,
    get_upload_root,
    is_file_owner,
    process_file_upload,
    record_download_audit,
    soft_delete_file,
    truncate_hash,
    verify_file_integrity,
    get_user_file_permission,
    has_read_permission,
    has_write_permission,
    get_pending_request,
    process_file_replacement,
)


def create_files_blueprint(login_required, get_db_connection, utc_now_str, base_dir, log_audit, create_notification):
    files_bp = Blueprint("files", __name__)
    upload_root = get_upload_root(base_dir)
    os.makedirs(upload_root, exist_ok=True)

    def current_user_id():
        return session["user_id"]

    @files_bp.route("/upload", methods=["GET", "POST"])
    @login_required
    def upload_page():
        if request.method == "POST":
            return upload_file()

        return render_template("upload.html", username=session.get("username"))

    @files_bp.route("/files/upload", methods=["POST"])
    @login_required
    def upload_file():
        uploaded_file = request.files.get("file")

        conn = get_db_connection()
        try:
            upload_time = utc_now_str()
            success, message, file_id = process_file_upload(
                conn,
                upload_root,
                current_user_id(),
                uploaded_file,
                upload_time,
            )
            if success:
                log_audit(conn, current_user_id(), file_id, "UPLOAD", f"Uploaded file '{uploaded_file.filename}'.")
                conn.commit()
                flash(message, "success")
            else:
                conn.rollback()
                flash(message, "danger")
        finally:
            conn.close()

        next_page = request.form.get("next") or request.referrer or url_for("dashboard")
        return redirect(next_page)

    @files_bp.route("/files/<int:file_id>")
    @login_required
    def file_details(file_id):
        conn = get_db_connection()
        try:
            file_record = get_file_by_id(conn, file_id, include_deleted=True)
            if not file_record:
                flash("File not found.", "danger")
                return redirect(url_for("dashboard"))

            # Enforce read permission
            if not has_read_permission(conn, file_id, current_user_id()):
                flash("You do not have permission to view this file's details. Request access first.", "warning")
                return redirect(url_for("dashboard"))

            file_record, audit_logs = get_file_audit_logs(conn, file_id)
            role = get_user_file_permission(conn, file_id, current_user_id())
            can_write = has_write_permission(conn, file_id, current_user_id())
        finally:
            conn.close()

        return render_template(
            "file_details.html",
            username=session.get("username"),
            file_record=file_record,
            audit_logs=audit_logs,
            formatted_size=format_file_size(file_record["file_size"]),
            truncated_hash=truncate_hash(file_record["sha256_hash"]),
            is_owner=is_file_owner(file_record, current_user_id()),
            role=role,
            can_write=can_write,
        )

    @files_bp.route("/files/<int:file_id>/download")
    @login_required
    def download_file(file_id):
        conn = get_db_connection()
        try:
            file_record = get_file_by_id(conn, file_id)
            if not file_record:
                flash("File not found.", "danger")
                return redirect(url_for("dashboard"))

            # Enforce read permission
            if not has_read_permission(conn, file_id, current_user_id()):
                flash("You do not have permission to download this file.", "danger")
                return redirect(url_for("dashboard"))

            absolute_path = get_file_absolute_path(
                upload_root,
                file_record["stored_filename"],
                file_record["owner_id"],
            )
            if not os.path.isfile(absolute_path):
                flash("Stored file could not be located.", "danger")
                return redirect(url_for("files.file_details", file_id=file_id))

            timestamp = utc_now_str()
            record_download_audit(conn, file_record, current_user_id(), timestamp)
            log_audit(conn, current_user_id(), file_id, "DOWNLOAD", f"Downloaded file '{file_record['original_filename']}'.")
            conn.commit()
        finally:
            conn.close()

        return send_file(
            absolute_path,
            as_attachment=True,
            download_name=file_record["original_filename"],
            mimetype=file_record["mime_type"],
        )

    @files_bp.route("/files/<int:file_id>/verify", methods=["POST"])
    @login_required
    def verify_file(file_id):
        conn = get_db_connection()
        try:
            file_record = get_file_by_id(conn, file_id)
            if not file_record:
                flash("File not found.", "danger")
                return redirect(url_for("dashboard"))

            # Enforce read permission
            if not has_read_permission(conn, file_id, current_user_id()):
                flash("You do not have permission to verify this file.", "danger")
                return redirect(url_for("dashboard"))

            timestamp = utc_now_str()
            success, message, new_status, _ = verify_file_integrity(
                conn,
                upload_root,
                file_record,
                current_user_id(),
                timestamp,
            )
            log_audit(conn, current_user_id(), file_id, "VERIFY", f"Verified integrity of '{file_record['original_filename']}'. Status: {new_status}")
            if new_status == "MODIFIED":
                create_notification(
                    conn,
                    file_record["owner_id"],
                    "TAMPER ALERT",
                    f"File '{file_record['original_filename']}' integrity verification failed! Current hash does not match original upload.",
                    "TAMPER_ALERT"
                )
            conn.commit()
            category = "success" if new_status == "ACTIVE" else "warning"
            flash(message, category)
        finally:
            conn.close()

        return redirect(url_for("files.file_details", file_id=file_id))

    @files_bp.route("/files/<int:file_id>/delete", methods=["POST"])
    @login_required
    def delete_file(file_id):
        conn = get_db_connection()
        try:
            file_record = get_owned_file(conn, file_id, current_user_id())
            if not file_record:
                flash("You do not have permission to delete this file.", "danger")
                return redirect(url_for("dashboard"))

            timestamp = utc_now_str()
            soft_delete_file(conn, file_record, current_user_id(), timestamp)
            log_audit(conn, current_user_id(), file_id, "DELETE", f"Soft deleted file '{file_record['original_filename']}'.")
            conn.commit()
            flash("File deleted successfully.", "success")
        finally:
            conn.close()

        return redirect(url_for("dashboard"))

    @files_bp.route("/files/<int:file_id>/request-access", methods=["GET", "POST"])
    @login_required
    def request_access(file_id):
        conn = get_db_connection()
        try:
            file_record = get_file_by_id(conn, file_id)
            if not file_record:
                flash("File not found.", "danger")
                return redirect(url_for("dashboard"))

            # Check if user is owner
            if file_record["owner_id"] == current_user_id():
                flash("You are the owner of this file.", "info")
                return redirect(url_for("files.file_details", file_id=file_id))

            # Check if user already has permissions
            existing_perm = get_user_file_permission(conn, file_id, current_user_id())
            if existing_perm:
                flash(f"You already have {existing_perm} access to this file.", "info")
                return redirect(url_for("files.file_details", file_id=file_id))

            # Check if there is already a pending request
            pending = get_pending_request(conn, file_id, current_user_id())

            if request.method == "POST":
                if pending:
                    flash("You already have a pending access request for this file.", "warning")
                    return redirect(url_for("dashboard"))

                requested_permission = request.form.get("requested_permission", "READ_ONLY")
                request_message = request.form.get("request_message", "").strip()

                if requested_permission not in ("READ_ONLY", "READ_WRITE"):
                    flash("Invalid permission level requested.", "danger")
                    return redirect(url_for("dashboard"))

                cursor = conn.execute(
                    """
                    INSERT INTO access_requests (file_id, requester_id, owner_id, requested_permission, status, request_message)
                    VALUES (?, ?, ?, ?, 'PENDING', ?)
                    """,
                    (file_id, current_user_id(), file_record["owner_id"], requested_permission, request_message),
                )
                request_id = cursor.lastrowid
                
                # Notify the owner
                create_notification(
                    conn,
                    file_record["owner_id"],
                    "Access Requested",
                    f"User '{session.get('username')}' has requested {requested_permission} access to your file '{file_record['original_filename']}'.",
                    "ACCESS_REQUEST"
                )

                # Log audit
                log_audit(conn, current_user_id(), file_id, "REQUEST_CREATED", f"Requested {requested_permission} access to '{file_record['original_filename']}'.")
                
                conn.commit()
                flash("Access request submitted successfully.", "success")
                return redirect(url_for("dashboard"))

        finally:
            conn.close()

        return render_template(
            "request_access.html",
            username=session.get("username"),
            file_record=file_record,
            pending=pending
        )

    @files_bp.route("/files/<int:file_id>/replace", methods=["POST"])
    @login_required
    def replace_file(file_id):
        uploaded_file = request.files.get("file")
        if not uploaded_file or not uploaded_file.filename:
            flash("No file selected.", "danger")
            return redirect(url_for("files.file_details", file_id=file_id))

        conn = get_db_connection()
        try:
            file_record = get_file_by_id(conn, file_id)
            if not file_record:
                flash("File not found.", "danger")
                return redirect(url_for("dashboard"))

            # Check write permission
            if not has_write_permission(conn, file_id, current_user_id()):
                flash("You do not have permission to replace the contents of this file.", "danger")
                return redirect(url_for("files.file_details", file_id=file_id))

            timestamp = utc_now_str()
            success, message = process_file_replacement(
                conn,
                upload_root,
                file_record,
                uploaded_file,
                current_user_id(),
                timestamp,
            )
            if success:
                log_audit(conn, current_user_id(), file_id, "UPLOAD", f"Replaced contents of file '{file_record['original_filename']}'.")
                
                # Notify the owner if actor is NOT owner
                if file_record["owner_id"] != current_user_id():
                    create_notification(
                        conn,
                        file_record["owner_id"],
                        "File Replaced",
                        f"User '{session.get('username')}' has replaced the contents of your file '{file_record['original_filename']}'.",
                        "SYSTEM_ALERT"
                    )

                conn.commit()
                flash(message, "success")
            else:
                conn.rollback()
                flash(message, "danger")
        finally:
            conn.close()

        return redirect(url_for("files.file_details", file_id=file_id))

    @files_bp.app_context_processor
    def inject_file_helpers():
        return {
            "format_file_size": format_file_size,
            "truncate_hash": truncate_hash,
        }

    return files_bp

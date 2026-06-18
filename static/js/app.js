/**
 * HashGuard - Client-side utilities
 */

document.addEventListener("DOMContentLoaded", function () {
    const forms = document.querySelectorAll("form[data-validate]");

    forms.forEach(function (form) {
        form.addEventListener("submit", function (event) {
            const requiredFields = form.querySelectorAll("[required]");
            let isValid = true;

            requiredFields.forEach(function (field) {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add("is-invalid");
                } else {
                    field.classList.remove("is-invalid");
                }
            });

            if (!isValid) {
                event.preventDefault();
            }
        });
    });

    const otpInput = document.getElementById("otp_code");
    if (otpInput) {
        otpInput.addEventListener("input", function () {
            this.value = this.value.replace(/\D/g, "").slice(0, 6);
        });
    }

    const resendBtn = document.getElementById("resendBtn");
    if (resendBtn) {
        let cooldown = 60;
        resendBtn.disabled = true;
        resendBtn.textContent = "Resend Code (" + cooldown + "s)";

        const interval = setInterval(function () {
            cooldown -= 1;
            if (cooldown <= 0) {
                clearInterval(interval);
                resendBtn.disabled = false;
                resendBtn.textContent = "Resend Code";
            } else {
                resendBtn.textContent = "Resend Code (" + cooldown + "s)";
            }
        }, 1000);
    }

    const alerts = document.querySelectorAll(".alert");
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.classList.add("fade");
            alert.style.opacity = "0";
            setTimeout(function () {
                alert.remove();
            }, 300);
        }, 5000);
    });

    const dropzones = document.querySelectorAll("[data-dropzone]");
    dropzones.forEach(function (dropzone) {
        const form = dropzone.closest("[data-upload-form]");
        const fileInput = dropzone.querySelector("[data-file-input]");
        const selectedFileLabel = dropzone.querySelector("[data-selected-file]");

        if (!form || !fileInput) {
            return;
        }

        function updateSelectedFileName(file) {
            if (!selectedFileLabel) {
                return;
            }
            selectedFileLabel.textContent = file ? file.name : "No file selected";
        }

        fileInput.addEventListener("change", function () {
            if (fileInput.files && fileInput.files.length > 0) {
                updateSelectedFileName(fileInput.files[0]);
            } else {
                updateSelectedFileName(null);
            }
        });

        ["dragenter", "dragover"].forEach(function (eventName) {
            dropzone.addEventListener(eventName, function (event) {
                event.preventDefault();
                event.stopPropagation();
                dropzone.classList.add("is-dragover");
            });
        });

        ["dragleave", "drop"].forEach(function (eventName) {
            dropzone.addEventListener(eventName, function (event) {
                event.preventDefault();
                event.stopPropagation();
                dropzone.classList.remove("is-dragover");
            });
        });

        dropzone.addEventListener("drop", function (event) {
            const files = event.dataTransfer.files;
            if (!files || files.length === 0) {
                return;
            }
            fileInput.files = files;
            updateSelectedFileName(files[0]);
        });
    });
});

function refreshCaptcha() {
    const captchaImg = document.getElementById("captcha-img");
    if (captchaImg) {
        captchaImg.src = "/captcha?t=" + new Date().getTime();
    }
}

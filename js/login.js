
const API_BASE_URL = window.COLLEGECONNECT_API_BASE_URL;

document.addEventListener("DOMContentLoaded", () => {
    const authForm = document.getElementById("authForm");
    const loginTab = document.getElementById("loginTab");
    const registerTab = document.getElementById("registerTab");
    const nameGroup = document.getElementById("nameGroup");
    const roleGroup = document.getElementById("roleGroup");
    const nameInput = document.getElementById("name");
    const passwordInput = document.getElementById("password");
    const submitButton = document.getElementById("submitAuth");
    const message = document.getElementById("authMessage");

    let mode = "login";

    function showMessage(text, type = "") {
        message.textContent = text;
        message.className = type;
    }

    function setMode(newMode) {
        mode = newMode;
        const registering = mode === "register";

        nameGroup.hidden = !registering;
        roleGroup.hidden = !registering;

        nameInput.required = registering;
        passwordInput.autocomplete = registering
            ? "new-password"
            : "current-password";

        loginTab.classList.toggle("active", !registering);
        registerTab.classList.toggle("active", registering);

        submitButton.textContent = registering ? "Create Account" : "Login";
        showMessage("");
    }

    loginTab.addEventListener("click", () => setMode("login"));
    registerTab.addEventListener("click", () => setMode("register"));

    authForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        showMessage("");

        const payload = {
            email: document.getElementById("email").value.trim(),
            password: passwordInput.value
        };

        if (mode === "register") {
            payload.name = nameInput.value.trim();
            payload.role = document.getElementById("role").value;
        }

        submitButton.disabled = true;
        submitButton.textContent =
            mode === "register" ? "Creating account..." : "Signing in...";

        try {
            const endpoint = mode === "register"
                ? "/api/register"
                : "/api/login";

            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || "Request failed.");
            }

            if (mode === "register") {
                showMessage(
                    "Account created! You can now log in.",
                    "success"
                );
                authForm.reset();
                setMode("login");
                showMessage("Account created! You can now log in.", "success");
            } else {
                showMessage("Login successful. Redirecting...", "success");

                // Keep this destination for the existing dashboard.
                
setTimeout(() => {
    const role = result.user.role;

    if (role === "student") {
        window.location.href = "dashboard.html";
    } else if (role === "cr") {
        window.location.href = "complaints.html";
    } else if (role === "professor") {
        window.location.href = "complaints.html";
    } else {
        window.location.href = "dashboard.html";
    }
}, 700);

            }
        } catch (error) {
            console.error("Authentication error:", error);
            showMessage(
                error instanceof TypeError
                    ? "Could not reach the CollegeConnect server. Make sure the backend is running."
                    : error.message || "Unable to complete the request.",
                "error"
            );
        } finally {
            submitButton.disabled = false;
            submitButton.textContent =
                mode === "register" ? "Create Account" : "Login";
        }
    });
});

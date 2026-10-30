const isLocalFrontend = ["localhost", "127.0.0.1"].includes(
    window.location.hostname
);
const apiHost = window.location.hostname || "127.0.0.1";
window.COLLEGECONNECT_API_BASE_URL = isLocalFrontend
    ? `http://${apiHost}:5000`
    : window.location.origin;

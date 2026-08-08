// -----------------------------------------------------------------
// Frontend configuration
// -----------------------------------------------------------------
// This is the ONLY place you need to change the backend address.
//
// By default this auto-detects:
//   - If this page is being served BY fastapi_app.py itself (the normal
//     way to run this now -- see GUI_README.md), it just uses the same
//     origin the page was loaded from, so nothing needs to change.
//   - If this page is opened directly as a file (file://), it falls back
//     to the default local backend address below.
//
// If your backend runs somewhere else (a different host/port, deployed
// remotely, etc.), just hardcode that URL here instead.
// -----------------------------------------------------------------

const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";

const CONFIG = {
  API_BASE_URL:
    window.location.protocol === "file:"
      ? DEFAULT_BACKEND_URL
      : window.location.origin,
};

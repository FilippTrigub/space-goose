# Plan for Google Docs AI Commenter Application

This document outlines the steps to create a Node.js application that allows users to log in with Google, view their recent Google Docs, get AI comments on a selected document, and view/edit the document content using Quill.js.

## 1. Project Setup

*   Create the `app` directory.
*   Navigate into the `app` directory: `cd app`
*   Initialize a Node.js project: `npm init -y`
*   Install core dependencies:
    ```bash
    npm install express express-session passport passport-google-oauth20 googleapis dotenv ejs
    ```
*   Install development dependency (optional, for auto-restarting server):
    ```bash
    npm install --save-dev nodemon
    ```
*   Create a basic `.gitignore` file (e.g., add `node_modules`, `.env`).
*   Create main application file (e.g., `server.js` or `app.js`).
*   Create necessary directories: `views`, `routes`, `config`, `public` (for static assets like CSS/JS), `services`.

## 2. Google OAuth Configuration

*   Go to the [Google Cloud Console](https://console.cloud.google.com/).
*   Create a new project or select an existing one.
*   Enable the "Google Drive API" and "Google Docs API".
*   Go to "Credentials", create "OAuth 2.0 Client IDs", select "Web application".
*   Configure Authorized JavaScript origins (e.g., `http://localhost:3000`).
*   Configure Authorized redirect URIs (e.g., `http://localhost:3000/auth/google/callback`).
*   Note the Client ID and Client Secret.
*   Create a `.env` file in the `app` directory and store the credentials:
    ```dotenv
    GOOGLE_CLIENT_ID=YOUR_CLIENT_ID
    GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET
    SESSION_SECRET=A_RANDOM_SECRET_STRING
    PORT=3000
    CALLBACK_URL=http://localhost:3000/auth/google/callback
    ```
*   Load environment variables using `dotenv` in `server.js`.

## 3. Authentication Setup (Passport.js)

*   Create `config/passport-setup.js`.
*   Configure the `passport-google-oauth20` strategy:
    *   Use the environment variables for Client ID, Secret, and Callback URL.
    *   Request necessary scopes: `profile`, `email`, `https://www.googleapis.com/auth/documents.readonly`, `https://www.googleapis.com/auth/drive.metadata.readonly`.
    *   Implement the `verify` callback function to find or create a user in a local database (or session for simplicity initially) and store the access token and refresh token securely associated with the user.
*   Configure Passport serialization/deserialization (`passport.serializeUser`, `passport.deserializeUser`).
*   In `server.js`:
    *   Configure `express-session` with the `SESSION_SECRET`.
    *   Initialize Passport: `app.use(passport.initialize()); app.use(passport.session());`.
    *   Import and use the Passport configuration.

## 4. Authentication Routes

*   Create `routes/auth.js`.
*   Define the login route (`/auth/google`): Use `passport.authenticate('google', { scope: [...] })`.
*   Define the callback route (`/auth/google/callback`): Use `passport.authenticate('google', { failureRedirect: '/login' })`, redirect to dashboard on success (`/dashboard`).
*   Define a logout route (`/logout`): Use `req.logout()`, destroy session, redirect to login page.
*   Define a simple login page route (`/login`) that renders a view with a "Login with Google" button.
*   Mount the auth routes in `server.js`.

## 5. Google API Service

*   Create `services/googleApi.js`.
*   Implement a function `getGoogleApiClient(accessToken)` that initializes and returns an authenticated Google API client (`google.auth.OAuth2` and `google.drive`, `google.docs`).
*   Implement `getRecentDocuments(authClient, count = 5)`:
    *   Uses the Drive API (`drive.files.list`) to fetch the latest `count` documents owned by or shared with the user.
    *   Parameters: `pageSize`, `orderBy='modifiedTime desc'`, `fields='files(id, name, modifiedTime)'`.
*   Implement `getDocumentContent(authClient, documentId)`:
    *   Uses the Docs API (`docs.documents.get`) to fetch the content of a specific document.
    *   Parameters: `documentId`, `fields='body'`. (May need refinement to get plain text or structured content suitable for Quill).

## 6. Core Application Routes & Views

*   Create `routes/index.js` (or similar).
*   Create middleware `ensureAuthenticated(req, res, next)` to protect routes.
*   **Dashboard Route (`/dashboard`)**:
    *   Protected by `ensureAuthenticated`.
    *   Get `authClient` using the stored access token.
    *   Call `getRecentDocuments`.
    *   Render a `dashboard.ejs` view, passing the list of documents.
*   **Document View Route (`/docs/:documentId`)**:
    *   Protected by `ensureAuthenticated`.
    *   Get `documentId` from `req.params`.
    *   Get `authClient`.
    *   Call `getDocumentContent`.
    *   Render a `document.ejs` view, passing the document content (and ID).
*   **Setup EJS**:
    *   `app.set('view engine', 'ejs');` in `server.js`.
    *   Create basic layout (`views/partials/header.ejs`, `views/partials/footer.ejs`).
    *   Create views: `views/login.ejs`, `views/dashboard.ejs`, `views/document.ejs`.

## 7. Frontend: Quill.js Integration

*   Include Quill.js CSS and JS from a CDN or install via npm and serve statically.
*   In `views/document.ejs`:
    *   Add a `div` container for the Quill editor (e.g., `<div id="editor"></div>`).
    *   Add JavaScript to:
        *   Initialize Quill on the `#editor` div when the page loads.
        *   Get the document content passed from the server route.
        *   Set the Quill editor's content (need to ensure format compatibility - may require processing the Google Doc content).
        *   Disable editing initially if desired, or allow it (changes are local only for now).
*   Add basic styling.

## 8. AI Integration (Placeholder)

*   Define a placeholder function (e.g., in `services/aiService.js`) `getAiComments(documentContent)` that returns a hardcoded array of comment objects (e.g., `{ text: "This section is well written." }`).
*   In the `/docs/:documentId` route, after fetching document content, call `getAiComments`.
*   Pass the comments to the `document.ejs` view.
*   In `document.ejs`, display the comments in a separate section next to or below the Quill editor.

## 9. Refinement & Deployment

*   Add error handling.
*   Improve UI/UX.
*   Secure session management.
*   Handle token expiration and refresh tokens (important for long-lived access).
*   Consider database integration for storing user information persistently.
*   Prepare for deployment (e.g., using environment variables for production, choosing a hosting provider).

## Future Enhancements (Optional)

*   Implement saving/syncing changes back to Google Docs.
*   Real-time collaboration features.
*   More sophisticated AI analysis and commenting.
*   User management and permissions. 
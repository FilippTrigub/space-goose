const { google } = require('googleapis');

/**
 * Creates an authenticated Google OAuth2 client.
 * @param {string} accessToken The user's access token.
 * @returns {google.auth.OAuth2} An authenticated OAuth2 client.
 */
function getAuthenticatedClient(accessToken) {
    const oauth2Client = new google.auth.OAuth2(
        process.env.GOOGLE_CLIENT_ID,
        process.env.GOOGLE_CLIENT_SECRET,
        process.env.CALLBACK_URL
    );
    oauth2Client.setCredentials({ access_token: accessToken });
    return oauth2Client;
}

/**
 * Fetches the most recently modified Google Docs documents.
 * @param {google.auth.OAuth2} authClient Authenticated Google OAuth2 client.
 * @param {number} [count=10] Number of documents to fetch.
 * @returns {Promise<Array<object>>} A promise that resolves to an array of document files.
 */
async function getRecentDocuments(authClient, count = 10) {
    const drive = google.drive({ version: 'v3', auth: authClient });
    try {
        const res = await drive.files.list({
            pageSize: count,
            orderBy: 'modifiedTime desc',
            // Fetch only Google Docs, owned by or shared with the user
            q: "mimeType='application/vnd.google-apps.document'",
            fields: 'files(id, name, modifiedTime, webViewLink)', // Added webViewLink
        });
        return res.data.files || [];
    } catch (error) {
        console.error('Error fetching recent documents:', error);
        // Handle potential token expiration/revocation here in a real app
        throw new Error('Failed to fetch documents from Google Drive.');
    }
}

/**
 * Fetches the content of a specific Google Document.
 * @param {google.auth.OAuth2} authClient Authenticated Google OAuth2 client.
 * @param {string} documentId The ID of the document to fetch.
 * @returns {Promise<object>} A promise that resolves to the Google Doc object (or specific parts like body).
 */
async function getDocumentContent(authClient, documentId) {
    const docs = google.docs({ version: 'v1', auth: authClient });
    try {
        const res = await docs.documents.get({
            documentId: documentId,
            // Requesting the body content. Adjust fields as needed.
            fields: 'body,documentId,title,inlineObjects', // Added title and inlineObjects
        });
        console.log(`Fetched content for doc ID: ${documentId}`);
        // console.log(JSON.stringify(res.data.body, null, 2)); // Log structure if needed
        return res.data; // Return the full document object for now
    } catch (error) {
        console.error(`Error fetching document content for ID ${documentId}:`, error);
        // Handle errors, e.g., document not found, permission issues
        throw new Error('Failed to fetch document content from Google Docs.');
    }
}

module.exports = {
    getAuthenticatedClient,
    getRecentDocuments,
    getDocumentContent,
    // Other API functions will be added here
}; 
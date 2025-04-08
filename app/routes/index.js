const router = require('express').Router();
const {
    getAuthenticatedClient,
    getRecentDocuments,
    getDocumentContent
} = require('../services/googleApi');
const { getAiComments } = require('../services/aiService');
const google = require('googleapis');

// Middleware to ensure user is authenticated
function ensureAuthenticated(req, res, next) {
    if (req.isAuthenticated()) {
        return next();
    }
    res.redirect('/auth/login');
}

// Dashboard route - protected
router.get('/dashboard', ensureAuthenticated, async (req, res) => {
    if (!req.user || !req.user.accessToken) {
        // Should not happen if ensureAuthenticated works, but good practice
        return res.redirect('/auth/login');
    }

    try {
        const authClient = getAuthenticatedClient(req.user.accessToken);
        const documents = await getRecentDocuments(authClient, 15); // Fetch 15 docs

        // We need to create this view
        res.render('dashboard', { user: req.user, documents: documents });
    } catch (error) {
        console.error('Error loading dashboard:', error);
        // Maybe render an error page or redirect with an error message
        res.status(500).send('Error loading dashboard data.');
        // Consider logging out the user if the token is invalid
        // req.logout(...);
        // res.redirect('/auth/login?error=token_invalid');
    }
});

// Document view route - protected
router.get('/docs/:documentId', ensureAuthenticated, async (req, res) => {
    const { documentId } = req.params;
    if (!req.user || !req.user.accessToken) {
        return res.redirect('/auth/login');
    }

    try {
        const authClient = getAuthenticatedClient(req.user.accessToken);
        const documentData = await getDocumentContent(authClient, documentId);

        // Convert content for Quill (basic version)
        const documentContentForQuill = JSON.stringify(documentData.body.content);
        const documentInlineObjects = documentData.inlineObjects ? JSON.stringify(documentData.inlineObjects) : '{}'; // Define and stringify inline objects
        const documentTitle = documentData.title || 'Untitled Document';

        // Call AI commenting service (placeholder)
        // Pass the raw content or the processed Quill content, depending on AI needs
        const aiComments = await getAiComments(documentData.body.content); // Using raw structure for now

        res.render('document', {
            user: req.user,
            documentId: documentId,
            documentTitle: documentTitle,
            documentContent: documentContentForQuill,
            documentInlineObjects: documentInlineObjects, // Pass inline objects to the template
            aiComments: aiComments
        });
    } catch (error) {
        console.error(`Error loading document ${documentId}:`, error);
        res.status(500).send(`Error loading document ${documentId}.`);
    }
});

// Image Proxy Route - fetches image content using user's auth
router.get('/image-proxy/:documentId/:objectId', ensureAuthenticated, async (req, res) => {
    const { documentId, objectId } = req.params;

    if (!req.user || !req.user.accessToken) {
        return res.status(401).send('Unauthorized');
    }

    try {
        const authClient = getAuthenticatedClient(req.user.accessToken);

        // We need the contentUri for the specific objectId
        // Fetch the document again, but only request the necessary inlineObject field
        const docs = google.google.docs({ version: 'v1', auth: authClient });
        const docData = await docs.documents.get({
            documentId: documentId,
            fields: 'inlineObjects' // Request the whole inlineObjects map
        });

        const inlineObject = docData.data.inlineObjects?.[objectId]; // Extract the specific object here
        const imageUri = inlineObject?.inlineObjectProperties?.embeddedObject?.imageProperties?.contentUri;

        if (!imageUri) {
            console.error(`Image URI not found for doc ${documentId}, object ${objectId}`);
            return res.status(404).send('Image not found in document data');
        }

        // Make an authenticated request to the imageUri
        // The authClient should automatically add the Authorization header
        const imageResponse = await authClient.request({ url: imageUri, responseType: 'stream' });

        // Determine content type (simplistic for now, might need improvement)
        let contentType = 'image/png'; // Default
        if (imageUri.includes('.jpg') || imageUri.includes('.jpeg')) {
            contentType = 'image/jpeg';
        } else if (imageUri.includes('.gif')) {
            contentType = 'image/gif';
        } // Add more types if needed
        // TODO: Check imageResponse headers for a more reliable content-type

        res.setHeader('Content-Type', contentType);
        imageResponse.data.pipe(res); // Pipe the image stream to the response

    } catch (error) {
        console.error(`Error proxying image doc ${documentId}, object ${objectId}:`, error);
        if (error.response?.status === 404) {
             return res.status(404).send('Image not found or access denied by Google');
        }
        res.status(500).send('Error fetching image');
    }
});

// Add other core routes here (e.g., document view)

module.exports = router; 
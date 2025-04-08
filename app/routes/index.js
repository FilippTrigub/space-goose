const router = require('express').Router();
const {
    getAuthenticatedClient,
    getRecentDocuments,
    getDocumentContent
} = require('../services/googleApi');
const { getAiComments } = require('../services/aiService');

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
        const documentTitle = documentData.title || 'Untitled Document';

        // Call AI commenting service (placeholder)
        // Pass the raw content or the processed Quill content, depending on AI needs
        const aiComments = await getAiComments(documentData.body.content); // Using raw structure for now

        res.render('document', {
            user: req.user,
            documentId: documentId,
            documentTitle: documentTitle,
            documentContent: documentContentForQuill,
            aiComments: aiComments
        });
    } catch (error) {
        console.error(`Error loading document ${documentId}:`, error);
        res.status(500).send(`Error loading document ${documentId}.`);
    }
});

// Add other core routes here (e.g., document view)

module.exports = router; 
const router = require('express').Router();
const passport = require('passport');

// Auth login - renders a simple login page
router.get('/login', (req, res) => {
    // We'll create this view later
    res.render('login', { user: req.user }); // Pass user if already logged in
});

// Auth logout
router.get('/logout', (req, res, next) => {
    req.logout(function(err) {
        if (err) { return next(err); }
        req.session.destroy((err) => {
            if (err) {
                console.log('Error : Failed to destroy the session during logout.', err);
            }
            req.user = null;
            res.redirect('/'); // Redirect to homepage or login page after logout
        });
    });
});

// Auth with Google
router.get('/google', passport.authenticate('google', {
    scope: [
        'profile',
        'email',
        'https://www.googleapis.com/auth/documents.readonly',
        'https://www.googleapis.com/auth/drive.metadata.readonly'
    ]
}));

// Callback route for Google to redirect to
router.get('/google/callback', passport.authenticate('google', { failureRedirect: '/login' }), (req, res) => {
    // Successful authentication, redirect dashboard.
    res.redirect('/dashboard'); // We'll create this route later
});

module.exports = router; 
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

// Route to start the Google authentication flow
router.get('/google', passport.authenticate('google', {
    scope: ['profile', 'email', 'openid', 'https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/docs']
}));

// Callback route Google redirects to after user grants permission
router.get('/google/callback',
    passport.authenticate('google', {
        failureRedirect: '/login-failure', // Redirect on failure
        // No scope needed here, this handles the response from Google
    }),
    (req, res) => {
        // Successful authentication!
        console.log('Authentication successful, user:', req.user.displayName);
        // The ID token was already posted to the internal service in passport-setup.js
        // Redirect the user to the terminal page.
        res.redirect('/terminal'); // Nginx will handle proxying this path
    }
);

// Error handler specifically for Passport authentication failures
router.use((err, req, res, next) => {
  if (err && err.message && err.message.includes('Failed to obtain access token')) {
    // Handle cases where Google rejects the request (e.g., consent screen cancel)
    console.warn('Authentication failed (likely user cancellation):', err.message);
    res.redirect('/?error=auth_cancelled'); // Redirect with error query param
  } else if (err) {
    // Handle other authentication errors (e.g., internal auth service failure)
    console.error('Authentication Error:', err);
    res.redirect('/?error=auth_failed'); // Redirect with generic error query param
  } else {
    next();
  }
});

module.exports = router; 
const passport = require('passport');
const GoogleStrategy = require('passport-google-oauth20').Strategy;
const fetch = require('node-fetch');

// IMPORTANT: Load these from environment variables in a real app
const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID || 'YOUR_GOOGLE_CLIENT_ID'; // TODO: Replace or set env var
const GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET || 'YOUR_GOOGLE_CLIENT_SECRET'; // TODO: Replace or set env var
const CALLBACK_URL = process.env.CALLBACK_URL || '/auth/google/callback'; // Relative path handled by nginx/app
const INTERNAL_AUTH_URL = 'http://mcp-gdrive-sse:8001/auth';

// Replace with a real user model/database interaction later
const users = {}; // Simple in-memory store for demonstration

passport.serializeUser((user, done) => {
    // Serialize user information (e.g., the user object received from Google or just the ID token)
    // What we store here will be available in req.user
    // Storing the ID token might be useful if the internal service needs it directly
    done(null, user); // Store the whole user object (including token) in the session
});

passport.deserializeUser((user, done) => {
    // Retrieve user information from the session
    // In this simple case, the serialized user object is sufficient
    done(null, user);
});

passport.use(
    new GoogleStrategy(
        {
            clientID: GOOGLE_CLIENT_ID,
            clientSecret: GOOGLE_CLIENT_SECRET,
            callbackURL: CALLBACK_URL, // The URL Google redirects to after user grants permission
            scope: ['profile', 'email', 'openid'], // openid is needed for id_token
        },
        async (accessToken, refreshToken, params, profile, done) => {
            // This function is called after successful authentication with Google
            const id_token = params.id_token; // Get the ID token

            console.log('Google Profile received:', profile.displayName, profile.emails?.[0]?.value);
            console.log('ID Token received (first 20 chars):', id_token ? id_token.substring(0, 20) + '...' : 'N/A');

            if (!id_token) {
                console.error('ID token not received from Google.');
                return done(new Error('ID token missing from Google response.'), null);
            }

            // *** Call the internal /auth endpoint ***
            try {
                console.log(`Posting ID token to internal service: ${INTERNAL_AUTH_URL}`);
                const response = await fetch(INTERNAL_AUTH_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'text/plain' }, // Assuming target takes plain text token
                    body: id_token,
                });

                if (!response.ok) {
                    const errorBody = await response.text();
                    console.error(`Error response from internal auth service ${INTERNAL_AUTH_URL}: ${response.status} ${response.statusText}`, errorBody);
                    // Decide if this failure should prevent login
                    // For now, let's pass an error to Passport
                    return done(new Error(`Internal auth service failed: ${response.statusText}`), null);
                }

                console.log(`Successfully posted token to internal service, status: ${response.status}`);

                // Authentication successful, proceed to serialize user
                // We can pass the profile info and the id_token to serializeUser
                const user = {
                    googleId: profile.id,
                    displayName: profile.displayName,
                    email: profile.emails?.[0]?.value,
                    id_token: id_token, // Include the ID token
                    // Add any other relevant info from profile
                };
                return done(null, user); // Pass user object to serializeUser

            } catch (error) {
                console.error('Error contacting internal auth service:', error);
                return done(error, null);
            }
        }
    )
); 
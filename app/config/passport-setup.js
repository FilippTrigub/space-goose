const passport = require('passport');
const GoogleStrategy = require('passport-google-oauth20').Strategy;

// Replace with a real user model/database interaction later
const users = {}; // Simple in-memory store for demonstration

passport.serializeUser((user, done) => {
    // Serialize user ID (or other identifier) to the session
    done(null, user.id);
});

passport.deserializeUser((id, done) => {
    // Deserialize user from the session using the ID
    const user = users[id]; // Find user in our simple store
    done(null, user);
});

passport.use(
    new GoogleStrategy({
        clientID: process.env.GOOGLE_CLIENT_ID,
        clientSecret: process.env.GOOGLE_CLIENT_SECRET,
        callbackURL: process.env.CALLBACK_URL,
        scope: [
            'profile',
            'email',
            'https://www.googleapis.com/auth/documents.readonly',
            'https://www.googleapis.com/auth/drive.metadata.readonly'
        ]
    },
    (accessToken, refreshToken, profile, done) => {
        // This is the verify callback
        console.log('Passport callback function fired:');
        console.log(profile);

        // Find or create user
        let user = users[profile.id];
        if (!user) {
            // Store user profile and tokens (IMPORTANT: Store tokens securely in a real app!)
            user = {
                id: profile.id,
                googleId: profile.id, // Redundant, but common practice
                displayName: profile.displayName,
                email: profile.emails[0].value, // Assuming at least one email
                accessToken: accessToken,
                refreshToken: refreshToken // Store refresh token if needed for offline access
            };
            users[profile.id] = user;
            console.log('Creating new user:', user);
        } else {
            // Update tokens if necessary
            user.accessToken = accessToken;
            user.refreshToken = refreshToken; // Update refresh token if provided
            console.log('Found existing user:', user);
        }

        // Pass the user object to Passport
        done(null, user);
    })
); 
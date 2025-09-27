# TODO: Session Message History Loading

## 📋 Task Overview
Load and display previous messages when an existing session is resumed.

## ✅ Implementation Steps

### 1. Backend API Enhancement
- [x] Add endpoint to fetch session message history
- [x] Use existing Goose API `/api/v1/sessions/{id}/messages` endpoint
- [x] Add proxy endpoint in k8s-manager to fetch messages

### 2. Frontend Message Loading
- [x] Load message history when session is selected
- [x] Display previous messages in chat output
- [x] Format messages with proper timestamps and roles
- [x] Show loading indicator while fetching history

### 3. Message Display Enhancement
- [x] Show message timestamps
- [x] Differentiate between historical and new messages
- [x] Proper message formatting for different types (user, assistant, tool)
- [x] Auto-scroll to bottom after loading history

### 4. User Experience
- [x] Show "Loading previous messages..." indicator
- [x] Clear message output before loading new session
- [x] Handle empty sessions gracefully
- [x] Show message count in session history header

## 🔧 Technical Implementation
- New endpoint: `GET /users/{user_id}/projects/{project_id}/sessions/{session_id}/messages`
- Frontend: Load messages when `selectSession()` is called
- Message format: Include timestamps and proper role indicators
- Error handling: Graceful fallback if message loading fails

## ✅ **IMPLEMENTATION COMPLETE!**

### Key Features Implemented:

1. **Backend Message History API**
   - ✅ New endpoint: `GET /users/{user_id}/projects/{project_id}/sessions/{session_id}/messages`
   - ✅ Proxies requests to Goose API `/api/v1/sessions/{id}/messages`
   - ✅ Proper authentication and project validation
   - ✅ Error handling for offline/missing sessions

2. **Frontend Session Resume**
   - ✅ Automatic message history loading when session is selected
   - ✅ "Loading previous messages..." indicator
   - ✅ Formatted message display with timestamps
   - ✅ Role-based message formatting (User/Assistant)
   - ✅ Auto-scroll to bottom after loading

3. **Enhanced User Experience**
   - ✅ Clear visual separation between history and new messages
   - ✅ Message count display in history header
   - ✅ Graceful handling of empty sessions
   - ✅ Seamless transition from history to new conversation

### Message History Display Format:
```
📝 Session History (3 messages)

🧑 User (2:30:15 PM): Hello, how are you?

🤖 Assistant (2:30:18 PM): Hello! I'm doing well, thank you for asking...

🧑 User (2:31:22 PM): Can you help me with Python?

───────────────────────────

✨ Ready to continue the conversation!
```

### Technical Implementation:
- ✅ Session history loads automatically on session selection
- ✅ Timestamps formatted using user's local time
- ✅ Proper error handling if history loading fails
- ✅ Visual indicators for loading states
- ✅ Seamless integration with existing message streaming

Users can now resume conversations with **full context** from previous messages! 🎯
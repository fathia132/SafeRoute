# Voice Trigger Feature - Setup & Integration Guide

## 📋 Overview

The voice trigger feature allows users to activate emergency alerts by saying a custom distress word (e.g., "Help", "Danger"). Two independent users requested this feature, and it's now fully implemented.

### Features Included:
- 🎤 Custom distress word activation
- 🔇 Silent alert (no visible indicator to attacker)
- 📍 Automatic location sharing on voice trigger
- 🎚️ Adjustable microphone sensitivity
- 📊 Voice alert history & statistics
- 🧪 Built-in test function

---

## 🚀 Quick Setup (5 minutes)

### Step 1: Copy Files to Your Project

```
SafeRoute/
├── templates/
│   ├── voice-trigger.html      ← ADD
│   ├── alert-history.html      ← ADD
│   └── ... (existing files)
├── static/
│   └── js/
│       └── voice-trigger.js    ← ADD
├── app.py                       ← REPLACE with app-with-voice.py
└── ... (other files)
```

### Step 2: Rename & Replace

```bash
# Backup your current app.py
cp app.py app.py.backup

# Use the new version with voice support
cp app-with-voice.py app.py
```

### Step 3: Update Your Dashboard

Add this button to your `dashboard.html`:

```html
<!-- Add to your dashboard navigation or settings area -->
<a href="/voice-trigger" class="btn btn-voice">
  🎤 Voice Trigger Settings
</a>

<!-- Optional: Add to emergency alerts section -->
<div class="voice-indicator" id="voiceStatus" style="display: none;">
  <span class="pulse">🎤</span> Voice Trigger Active
</div>
```

### Step 4: Optional - Add to CSS

```css
.btn-voice {
  background: #4CAF50;
  color: white;
  padding: 12px 20px;
  border-radius: 8px;
  text-decoration: none;
  display: inline-block;
  margin-top: 10px;
  transition: all 0.3s;
}

.btn-voice:hover {
  background: #45a049;
  transform: translateY(-2px);
}

.voice-indicator {
  background: #d4edda;
  border: 1px solid #c3e6cb;
  color: #155724;
  padding: 10px 15px;
  border-radius: 8px;
  margin: 10px 0;
  font-weight: 600;
}

.pulse {
  display: inline-block;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.1); }
}
```

### Step 5: Test It

```bash
python app.py

# Visit: http://localhost:5000/voice-trigger
# Set your distress word (default: "help")
# Click "Test Your Distress Word"
# Say your distress word
# Check if it's recognized
```

---

## 🎯 How It Works

### User Flow

1. **User enables voice trigger** on `/voice-trigger` page
2. **Sets custom distress word** (e.g., "Help", "Danger")
3. **Adjusts sensitivity** (how strict the voice match needs to be)
4. **App listens in background** - continuously monitors for the word
5. **Word detected** → **Silent emergency alert** → **Location sent to contacts**
6. **Notification popup** → User sees alert was sent

### Technical Flow

```
[User speaks distress word]
         ↓
[Web Speech API captures audio]
         ↓
[JavaScript processes speech]
         ↓
[Compares to saved distress word]
         ↓
[Confidence score checked against sensitivity]
         ↓
[If confident match → Trigger emergency]
         ↓
[Get GPS location via Geolocation API]
         ↓
[Send POST to /emergency endpoint]
         ↓
[Flask backend sends SMS via Twilio]
         ↓
[Alert logged in database]
```

---

## 🔧 Customization Options

### Change Default Distress Word

In `voice-trigger.js` or `voice-trigger.html`:
```javascript
// Default distress word
value="help"  // Change to: "danger", "sos", "help me", etc.
```

### Adjust Default Sensitivity

```javascript
// In voice-trigger.js constructor
this.sensitivity = parseFloat(localStorage.getItem('voiceSensitivity') || 0.7);
// 0.3 = Very sensitive (catches variations)
// 0.5 = Medium
// 0.9 = Strict (exact match required)
```

### Change Language

In `voice-trigger.js`:
```javascript
// Current: English (US)
this.recognition.language = 'en-US';

// Change to other languages:
// 'es-ES' (Spanish)
// 'fr-FR' (French)
// 'de-DE' (German)
// 'pt-BR' (Portuguese)
// 'yo-NG' (Yoruba - Nigeria)
```

---

## 📱 Browser Support

| Browser | Desktop | Mobile |
|---------|---------|--------|
| Chrome | ✅ | ✅ |
| Edge | ✅ | ✅ |
| Safari | ✅ | ✅ (iOS 14.5+) |
| Firefox | ❌ | ❌ |
| Opera | ✅ | ✅ |

**Note:** Firefox doesn't support Web Speech API. Users will see a browser compatibility message.

---

## 🔐 Security & Privacy

### Data Collection
- ❌ Voice recordings are **NOT stored**
- ❌ Audio is **NOT sent to servers**
- ✅ Processing happens **locally in browser**
- ✅ Only emergency alert data is sent (with location)

### Privacy Controls
- User can **disable voice trigger anytime**
- User **controls their distress word**
- User can **adjust sensitivity** to avoid false triggers
- **Requires microphone permission** (browser prompts user)

### Best Practices for Users
1. Use a distinctive distress word (not common words)
2. Test voice recognition in quiet environment first
3. Adjust sensitivity if getting false triggers
4. Keep emergency contacts list up to date
5. Check alert history to verify alerts were sent

---

## 🐛 Troubleshooting

### Issue: "Voice recognition not supported"

**Fix:** Check browser compatibility
- ✅ Use Chrome, Edge, or Safari
- ❌ Firefox not supported
- ❌ Internet Explorer not supported

### Issue: Voice trigger not detecting word

**Solutions:**
1. **Speak louder** - App might be too sensitive
2. **Test first** - Use "Test Your Distress Word" button
3. **Reduce sensitivity** - Move slider to right (less strict)
4. **Different word** - Try simpler word without accents
5. **Check microphone** - Test microphone in browser settings

### Issue: False triggers (triggering on wrong words)

**Fix:** Increase sensitivity (move slider right) to require exact match

### Issue: "Couldn't connect with server" on emergency alert

**Fix:** Same as login issue - ensure Flask app is running and API URL is correct

---

## 📊 Monitoring Voice Alerts

### View Alert History

Navigate to `/alert-history` to see:
- Total alerts triggered
- How many were voice vs manual
- Contacts notified for each alert
- Timestamp of each alert
- Location coordinates

### Check Statistics

```bash
# Via API endpoint
curl http://localhost:5000/alert-stats

# Returns:
{
  "success": true,
  "total_alerts": 5,
  "voice_alerts": 2,
  "manual_alerts": 3,
  "contacts_reached": 12
}
```

---

## 🚀 Deployment Notes

### On Railway

1. All voice processing happens **in the browser** - no changes needed
2. Voice trigger works **as-is** on production URL
3. Just ensure `/voice-trigger` route is accessible
4. Test after deployment with `https://your-app.railway.app/voice-trigger`

### Performance Impact

- ✅ **No server load** (processing is client-side)
- ✅ **Minimal battery drain** (only during active listening)
- ✅ **Works offline** (local speech recognition)
- ⚠️ Requires **continuous microphone access** when enabled

---

## 🎓 Code Examples

### Integrate Voice Status in Dashboard

```javascript
// Check if voice trigger is enabled
function checkVoiceStatus() {
  const voiceEnabled = localStorage.getItem('voiceEnabled') === 'true';
  const voiceIndicator = document.getElementById('voiceStatus');
  
  if (voiceEnabled) {
    voiceIndicator.style.display = 'block';
  } else {
    voiceIndicator.style.display = 'none';
  }
}

// Call on dashboard load
document.addEventListener('DOMContentLoaded', checkVoiceStatus);
```

### Manual Emergency Trigger (existing)

```javascript
async function triggerEmergency() {
  const response = await fetch('/emergency', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      latitude: lat,
      longitude: lng,
      trigger_type: 'manual'
    })
  });
}
```

### Voice-triggered Emergency (automatic)

```javascript
// Handled by voice-trigger.js - no manual coding needed
// When distress word is detected:
// - Gets location automatically
// - Sends POST to /emergency with trigger_type: 'voice'
// - Shows notification to user
```

---

## 📝 Files Included

| File | Purpose |
|------|---------|
| `voice-trigger.html` | Settings page where users configure voice |
| `voice-trigger.js` | Speech recognition logic & alert triggering |
| `alert-history.html` | Dashboard showing all alerts triggered |
| `app-with-voice.py` | Updated Flask app with voice routes |

---

## ✅ Testing Checklist

Before deploying to production:

- [ ] Can enable/disable voice trigger
- [ ] Can set custom distress word
- [ ] Sensitivity slider works
- [ ] Test button detects spoken word
- [ ] False positives are rare
- [ ] Emergency alert sent when word detected
- [ ] Location is shared in SMS
- [ ] Alert appears in history
- [ ] Works on mobile browser
- [ ] Works offline (app already running)
- [ ] No constant battery drain

---

## 🎤 Voice Trigger is Live!

Your users can now:
- Say their custom distress word
- Get emergency help without touching the screen
- Maintain privacy (silent activation)
- Have full control over settings

This addresses the feature request from 2 independent users perfectly. 🎉

---

## 📞 Support & Future Enhancements

### Potential Phase 2 Features:
- Audio recording for evidence
- Voice pattern recognition (stress detection)
- Multiple distress phrases
- Offline recording (no connection)
- Automatic police audio file submission

### Feedback?
Open an issue on GitHub or contact the development team.

---

**Voice Trigger Feature Ready! 🎤✨**
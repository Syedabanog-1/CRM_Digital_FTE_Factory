# TechCorp Support Form

Standalone, embeddable web support form for the TechCorp Customer Success Digital FTE.

## Integration

### Option 1: Script Tag

```html
<div id="techcorp-support-form"></div>
<script>
  window.TECHCORP_API_URL = 'https://fte.techcorp.com';
</script>
<script src="path/to/support-form.js"></script>
```

### Option 2: React Import

```jsx
import SupportForm from 'techcorp-support-form/src/SupportForm';

function App() {
  return <SupportForm />;
}
```

## Configuration

Set these globals before loading:

- `window.TECHCORP_API_URL` - Backend API URL (default: `http://localhost:8000`)
- `window.TECHCORP_FORM_TARGET` - Target element ID (default: `techcorp-support-form`)

## Development

```bash
npm install
npm start
```

## Features

- Client-side validation (name, email, subject, message)
- Category and priority selection
- Ticket ID confirmation on submission
- Ticket status checking
- Form reset for new requests

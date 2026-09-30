# Ukrainian and English

Interface phrases are translated locally, without a service or API key.
The existing base template catalogue is supplemented by `app/static/ui-en.js`.
Add complete phrases; do not substitute words inside sentences. Dropdown labels
are translated without changing submitted values. Dynamic text, placeholders,
titles and accessibility labels are processed when the language changes.
Language is remembered in browser storage. Names and editable form values are
not machine-translated.

News, event, survey, community link and KPI import text uses marked content fields.
The browser first uses known translations. Unknown Cyrillic content is translated
by the server through DeepL, then cached in `content_translations` using a hash of
the source text. Editing the source invalidates the relevant cache entry.
The original database content remains unchanged. Private messages, survey
responses and unpublished news are not exposed through the public endpoint.
KPI review entries require an administrator session. Public article text is sent
to DeepL; the API key is never sent to the browser.

## Enable automatic translation

Create a DeepL API account (a normal translator subscription is not the same).
Put its API key privately in the local `.env` file or hosting environment:

```dotenv
DEEPL_API_KEY=your_private_api_key
```

Restart the application. Keys ending in `:fx` use the Free API endpoint; other
keys use the Pro endpoint. Check your account's limits and billing settings.
No account, subscription or payment is created automatically by this code.
Provider documentation: https://developers.deepl.com/docs/getting-started/intro

Without a key, or if the service is unavailable, untranslatable content remains
in its original language and the English view shows a notice. A reload retries
failed translations. API failures do not cache untranslated text as English.
Existing successful translations can still be served from the database cache.

Interface tests can run without a key. Provider tests use mocked responses;
successful real translation needs verification after the key is configured.

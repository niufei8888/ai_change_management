---
title: Luma Extensions
slug: luma-extensions
url: https://lumalabs.ai/learning-center/articles/luma-extensions
---

June 14, 2026

## Intro to Extensions in Luma

An **extension** links Luma to a tool where your work already lives — Google Drive, Dropbox, Frame.io, Box, or Airtable — so Luma can bring that material straight into your workflow instead of you downloading, re-uploading, and copy-pasting between tabs.

### Read-and-add

Extensions are built on a **read-and-add** model. Luma can **read, import, create, upload, and save** work — but it can **never delete, rename, or overwrite** anything in your connected account.

- ✅ Find and read your files
- ✅ Pull media and documents onto the canvas
- ✅ Save finished work *back* to the connected service
- ✅ Create or update records (Airtable)
- ❌ Delete your files
- ❌ Rename your files
- ❌ Overwrite existing files

Those destructive actions simply aren't available to the Agent. This is the core trust principle: extensions help Luma work with the material you choose — they don't take control of your storage.

### The five extensions

#### Google Drive
Best for: Specific Docs, Sheets, Slides & individual files you pick for Luma

#### Dropbox
Best for: Finding files across your storage by name (best search)

#### Frame.io
Best for: Footage, cuts, and timecoded review feedback

#### Box
Best for: Enterprise folder storage (browse-based import/export)

#### Airtable
Best for: Structured records — trackers, asset lists, databases

### How connecting works

1. Go to the **Extensions page** to manage extensions.
2. When you connect, Luma sends you through the service's **normal sign-in** (standard OAuth). You log in on the provider's own window and approve a permission screen there.
3. **Luma never sees or stores your password** — it receives an access token scoped to what you approved. Each connection card shows which account it's tied to (usually the email).

#### Good to know:
- **Connections are personal and per-team.** Your teammates don't share your connection or see your files, and connecting a service in one Luma team doesn't carry over to another.
- **Admins control availability.** Every extension is off by default; a team admin decides which are available. On enterprise teams an extension may appear grayed out until an admin enables it.

### Pause vs. Disconnect

- **Pause** = a temporary off switch. Hides the extension's tools from the Agent but keeps the connection alive — resume later with no new login.
- **Disconnect** = removes access. Revokes Luma's access (usually at the provider level too).

Use **pause** when you just want the Agent to leave it alone for now. Use **disconnect** when you want access gone.

### Use Extensions With The Agent

No special commands. Talk in plain language:

`Read the Google Doc I picked and turn it into a shot list.`

`Find the file called 'Q3 brief' in my Dropbox and make a 5m slide deck with speaker notes.`

`Summarize the review feedback on my latest Frame.io cut with the timecodes.`

`Pull the product list from my Airtable and make a visual for each record.`

`Save this finished image back to my Box folder.`

### What each extension can (and can't) do

#### Google Drive

- **Can:** Search and read files **you've picked** for Luma; read Docs/Sheets/Slides as text; import files to the canvas; save new files back; create new native Google Docs.
- **Can't:** See your *whole* Drive; modify, delete, rename, or overwrite files.
- **Know this:** Drive uses a **narrow permission model** — Luma only sees files you explicitly pick in the Google file picker (plus files Luma created). The #1 confusion is *"why can't Luma find my file?"* — usually it just hasn't been picked yet. **Fix: pick the file, don't reconnect.** Google-native files come in as editable Office equivalents (Docs→Word, Sheets→Excel, Slides→PowerPoint).

#### Dropbox

- **Can:** **Search your whole Dropbox by file name** (the strongest search of the five); browse folders; read files; import to canvas; save files back. Same-name saves are **auto-renamed**, never overwritten.
- **Can't:** Modify, delete, rename, or overwrite files. On **free plans**, can't search *inside* file contents (a Dropbox tier limit).
- **Know this:** Dropbox grants whole-account access at connect time, which is why it's great for "find that file" workflows.

#### Frame.io

- **Can:** Browse accounts, workspaces, projects, folders; import video/media to the canvas; upload finished videos back; **read review comments with exact timecodes**; see version stacks. Ideal for creative review.
- **Can't:** Search (navigate via folders/projects instead); interpret drawn annotations (it knows one exists but not what it depicts).
- **Know this:** Freshly uploaded media may still be transcoding — importing immediately may need a retry. On reconnect, Adobe may skip the permission screen (it remembers prior approval) — that's provider behavior.

#### Box

- **Can:** Browse folders; read files; import to canvas; upload new files back; large/chunked uploads (above 50 MB).
- **Can't:** Search (browse-only); delete, rename, or overwrite.
- **Know this:** Box adds an extra security layer — each session Luma uses downgraded, short-lived credentials without delete/rename permissions, so the read-and-add guarantee is enforced by Box itself. Freshly uploaded files may need a moment (the Agent retries).

#### Airtable

- **Can:** Read bases, table schemas, records, and comments; **create and update records** (up to 10 per operation); download attachments to the canvas; upload new attachments.
- **Can't:** Delete records; free-text search (filters by field values instead); return more than 100 rows per request.
- **Know this:** Updates are additive and controlled. The 100-row cap is intentional — for big tables, filter to the relevant records. Rate-limited to 5 requests/sec per base (auto-handled). On disconnect, Airtable has no remote-revoke API, so the app may linger in your Airtable settings up to 60 days — remove it manually to speed that up.

### Which extension should you use?

- **Google Drive** — work with specific Docs, Sheets, Slides, or files you've picked.
- **Dropbox** — have the Agent *find* files across your storage by name.
- **Frame.io** — bring in footage, review cuts, and summarize timecoded feedback.
- **Box** — enterprise folder storage with browse-based import/export and strong permissions.
- **Airtable** — structured records: trackers, asset lists, production databases.

### Common questions

**Do I need to be technical?** No. If you can pick or share a file and describe what you want, you can use extensions.

**Is my material safe?** Yes — Luma never sees your password, access is scoped to what you approve, extensions can't delete or overwrite anything, and you can pause or disconnect anytime.

**Why can't Luma find my file?** Usually extension-specific: on Drive, the file hasn't been *picked* yet; on Frame.io/Box there's no search (browse instead); on Airtable, filter by field values. It can also be provider permissions or file size.

**Can Luma change or delete things in my account?** No. Extensions are read-and-add — they can add and save work, never delete, rename, or overwrite.

### Key takeaway

Extensions let Luma work with files, media, review notes, and structured data from the tools you already use — while keeping access **personal, permissioned, and non-destructive**. Each one is tuned for a different job: picked Drive files, Dropbox search, Frame.io review, Box storage, or Airtable records.

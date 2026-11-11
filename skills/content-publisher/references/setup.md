# Publishing setup

One-time setup so `publish.py` can post to **your own** account through Meta's
official API. You never give anyone your Instagram password: you create a token
in your own Meta developer app, and you can revoke it at any time.

Meta changes its dashboard often. If a screen looks different from these steps,
follow Meta's current guide: https://developers.facebook.com/documentation/instagram-platform/content-publishing

## 1. Requirements

- An Instagram **professional account** (Business or Creator). Switch in the app: Settings > Account type and tools.
- A Meta developer account: https://developers.facebook.com (log in with Facebook).
- Somewhere to host media at a public HTTPS URL (step 6).

## 2. Create a Meta app

1. developers.facebook.com > My Apps > Create app.
2. Choose the use case for managing messaging and content on Instagram (the Instagram API).
3. In the app, open the Instagram product's **API setup with Instagram login**.

## 3. Add your Instagram account

In the Instagram API setup screen, add your professional account (you may need to
add it as an Instagram tester under App roles and accept the invite in the
Instagram app). While the app stays in development mode and only you use it,
Meta's App Review is normally not required for your own account; check the
dashboard if it asks.

## 4. Permissions

The token needs:
- `instagram_business_basic`
- `instagram_business_content_publish`

(Using Facebook Login for Business instead? Then the host is `graph.facebook.com`,
the permissions are `instagram_basic`, `instagram_content_publish`,
`pages_read_engagement`, and the account must be connected to a Facebook Page.
Set `IG_API_HOST=graph.facebook.com`.)

## 5. Generate a token and keep it out of the repo

Generate an access token for your account in the API setup screen. Then, in the
terminal where you run the skills:

```sh
export IG_ACCESS_TOKEN='paste-token-here'      # this shell only
python3 scripts/publish.py account            # should print your @username and quota
```

Or keep it in a file outside the repo and point to it:

```sh
mkdir -p ~/.creator-content-kit && chmod 700 ~/.creator-content-kit
printf '%s' 'paste-token-here' > ~/.creator-content-kit/ig-token && chmod 600 ~/.creator-content-kit/ig-token
export IG_ACCESS_TOKEN_FILE=~/.creator-content-kit/ig-token
```

Never paste the token into a file inside this repository, into a post.json, or
into a chat you would share. Tokens expire; when `publish.py` reports code 190,
generate a new one here.

## 6. Host your media

Instagram downloads each file from a URL at the moment you publish, so the URL
must open in a private browser window without logging in.

- Images: **JPEG only** (`.jpg`). carousel-creator makes SVG slides; export them
  to JPEG (any design tool or image converter), 1080x1350 for portrait.
- Video: MP4 or MOV.
- Hosting: your own website, or a storage bucket with public file URLs (for
  example Amazon S3, Cloudflare R2, Google Cloud Storage). Links to share pages
  (Google Drive, Dropbox previews) do not work; you need the direct file URL.
- You can remove the files after the post is live.

## 7. First post

```sh
python3 scripts/publish.py check my-post.json          # preview + approval code
python3 scripts/publish.py publish my-post.json --approve CODE --dry-run
python3 scripts/publish.py publish my-post.json --approve CODE
```

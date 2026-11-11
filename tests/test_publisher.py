"""content-publisher: approval, validation and the API call sequence, against a fake Graph API (no network)."""

import argparse
import io
import json
import os
import shutil
import tempfile
import unittest
import urllib.parse
from contextlib import redirect_stdout

import helpers

EX = os.path.join(helpers.SKILLS, "content-publisher", "examples")


class FakeGraph:
    """Answers like the Graph API. statuses: container id -> list of status_code values to return in order."""

    def __init__(self, statuses=None, quota=(3, 50), fail=None):
        self.calls = []
        self.n = 0
        self.statuses = statuses or {}
        self.quota = quota
        self.fail = fail or {}

    def __call__(self, method, url, data, timeout):
        parts = urllib.parse.urlsplit(url)
        q = dict(urllib.parse.parse_qsl(parts.query))
        params = dict(data or q)
        path = parts.path.split("/", 2)[2]  # drop "/v27.0/"
        self.calls.append({"method": method, "host": parts.hostname, "path": path,
                           "params": {k: v for k, v in params.items() if k != "access_token"},
                           "token_sent": params.get("access_token")})
        key = (method, path.split("/")[-1])
        if key in self.fail:
            return 400, json.dumps({"error": {"message": "Bad thing with token %s" % params.get("access_token"),
                                              "code": self.fail[key]}})
        if method == "GET" and path == "me":
            return 200, json.dumps({"user_id": "17840000", "username": "priyabakes"})
        if path.endswith("content_publishing_limit"):
            used, total = self.quota
            return 200, json.dumps({"data": [{"quota_usage": used, "config": {"quota_total": total}}]})
        if method == "POST" and path.endswith("/media"):
            self.n += 1
            return 200, json.dumps({"id": "c%d" % self.n})
        if method == "POST" and path.endswith("/media_publish"):
            return 200, json.dumps({"id": "m1"})
        if method == "GET" and q.get("fields", "").startswith("status_code"):
            seq = self.statuses.get(path, ["FINISHED"])
            code = seq.pop(0) if len(seq) > 1 else seq[0]
            return 200, json.dumps({"status_code": code, "status": "x"})
        if method == "GET" and q.get("fields") == "permalink":
            return 200, json.dumps({"permalink": "https://www.instagram.com/p/FAKE/"})
        return 404, json.dumps({"error": {"message": "unknown fake path " + path}})

    def posts(self):
        return [c for c in self.calls if c["method"] == "POST"]


class PublisherTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = helpers.load_script("content-publisher", "publish")
        cls.api = helpers.load_script("content-publisher", "igapi")

    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.env = {k: os.environ.get(k) for k in ("IG_AGENT_HOME", "IG_ACCESS_TOKEN", "IG_USER_ID", "IG_ACCESS_TOKEN_FILE")}
        os.environ["IG_AGENT_HOME"] = self.home
        os.environ["IG_ACCESS_TOKEN"] = "TOKEN-SECRET-123"
        os.environ.pop("IG_USER_ID", None)
        os.environ.pop("IG_ACCESS_TOKEN_FILE", None)
        self.ctx = {"profile": helpers.fixture_profile()}
        self.cfg = self.m.config()
        self.cfg["polling"] = {"interval_seconds": 0, "attempts": 5}

    def tearDown(self):
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.home, ignore_errors=True)

    def code_for(self, name):
        post, cap = self.m.load_post(os.path.join(EX, name))
        return self.m.approval_code(post, cap)

    def run_publish(self, name, code=None, fake=None, **kw):
        fake = fake or FakeGraph()
        args = argparse.Namespace(post=os.path.join(EX, name), approve=code or self.code_for(name),
                                  dry_run=kw.get("dry_run", False), again=kw.get("again", False))
        out = []
        orig = self.m.config
        self.m.config = lambda: self.cfg
        try:
            rc = self.m.cmd_publish(args, self.ctx, transport=fake, say=out.append)
        finally:
            self.m.config = orig
        return rc, "\n".join(out), fake

    # -- approval ---------------------------------------------------------
    def test_code_changes_with_any_edit(self):
        post, cap = self.m.load_post(os.path.join(EX, "post-image.json"))
        code = self.m.approval_code(post, cap)
        self.assertRegex(code, r"^[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}$")
        self.assertNotEqual(code, self.m.approval_code(post, cap + "!"))
        post2 = json.loads(json.dumps(post))
        post2["media"][0]["url"] = post2["media"][0]["url"].replace("rescue", "rescue2")
        self.assertNotEqual(code, self.m.approval_code(post2, cap))
        self.assertEqual(code, self.m.approval_code(json.loads(json.dumps(post)), cap))  # deterministic

    def test_wrong_code_is_refused_before_any_call(self):
        rc, out, fake = self.run_publish("post-image.json", code="0000-0000-0000")
        self.assertEqual(rc, 2)
        self.assertIn("does not match", out)
        self.assertEqual(fake.calls, [])

    def test_blocked_post_cannot_publish_even_with_its_code(self):
        rc, out, fake = self.run_publish("post-bad.json")
        self.assertEqual(rc, 2)
        self.assertIn("blocked", out)
        self.assertEqual(fake.calls, [])

    def test_no_token(self):
        os.environ.pop("IG_ACCESS_TOKEN")
        rc, out, fake = self.run_publish("post-image.json")
        self.assertEqual(rc, 3)
        self.assertIn("Never use your Instagram password", out)

    def test_dry_run_sends_nothing(self):
        rc, out, fake = self.run_publish("post-carousel.json", dry_run=True)
        self.assertEqual(rc, 0)
        self.assertEqual(fake.calls, [])
        self.assertEqual(out.count("POST /<IG_ID>/media "), 5)  # 4 children + parent
        self.assertNotIn("TOKEN-SECRET", out)

    # -- the call sequence ---------------------------------------------------
    def test_image_flow_and_log(self):
        rc, out, fake = self.run_publish("post-image.json")
        self.assertEqual(rc, 0, out)
        posts = fake.posts()
        self.assertEqual([p["path"] for p in posts], ["17840000/media", "17840000/media_publish"])
        self.assertEqual(posts[0]["params"]["image_url"], "https://cdn.example.com/priya/starter-rescue.jpg")
        self.assertIn("alt_text", posts[0]["params"])
        self.assertTrue(posts[0]["params"]["caption"].startswith("Stop throwing out"))
        self.assertEqual(posts[1]["params"]["creation_id"], "c1")
        self.assertIn("https://www.instagram.com/p/FAKE/", out)
        self.assertTrue(all(c["host"] == "graph.instagram.com" for c in fake.calls))
        self.assertTrue(all(c["token_sent"] == "TOKEN-SECRET-123" for c in fake.calls))
        log = helpers.load_json(os.path.join(self.home, "publish-log.json"))
        self.assertEqual(log["published"][0]["media_id"], "m1")
        self.assertNotIn("TOKEN-SECRET", json.dumps(log))
        # the same post again is refused unless --again
        rc2, out2, fake2 = self.run_publish("post-image.json")
        self.assertEqual(rc2, 2)
        self.assertIn("already published", out2)
        self.assertEqual(fake2.posts(), [])
        rc3, _, fake3 = self.run_publish("post-image.json", again=True)
        self.assertEqual(rc3, 0)

    def test_carousel_children_then_parent(self):
        rc, out, fake = self.run_publish("post-carousel.json")
        self.assertEqual(rc, 0, out)
        creates = [p for p in fake.posts() if p["path"].endswith("/media")]
        self.assertEqual(len(creates), 5)
        for child in creates[:4]:
            self.assertEqual(child["params"]["is_carousel_item"], "true")
            self.assertNotIn("caption", child["params"])
        self.assertEqual(creates[3]["params"]["media_type"], "VIDEO")
        parent = creates[4]["params"]
        self.assertEqual(parent["media_type"], "CAROUSEL")
        self.assertEqual(parent["children"], "c1,c2,c3,c4")
        self.assertIn("caption", parent)
        self.assertEqual(fake.posts()[-1]["params"]["creation_id"], "c5")

    def test_reel_params_and_polling(self):
        fake = FakeGraph(statuses={"c1": ["IN_PROGRESS", "IN_PROGRESS", "FINISHED"]})
        rc, out, fake = self.run_publish("post-reel.json", fake=fake)
        self.assertEqual(rc, 0, out)
        p = fake.posts()[0]["params"]
        self.assertEqual(p["media_type"], "REELS")
        self.assertEqual(p["share_to_feed"], "true")
        self.assertEqual(p["thumb_offset"], "1500")
        polls = [c for c in fake.calls if c["path"] == "c1" and c["params"].get("fields", "").startswith("status_code")]
        self.assertEqual(len(polls), 3)

    def test_container_error_publishes_nothing(self):
        rc, out, fake = self.run_publish("post-reel.json", fake=FakeGraph(statuses={"c1": ["ERROR"]}))
        self.assertEqual(rc, 2)
        self.assertIn("is ERROR", out)
        self.assertFalse(any(p["path"].endswith("media_publish") for p in fake.posts()))
        self.assertFalse(os.path.exists(os.path.join(self.home, "publish-log.json")))

    def test_slow_video_gives_up_without_publishing(self):
        rc, out, fake = self.run_publish("post-reel.json", fake=FakeGraph(statuses={"c1": ["IN_PROGRESS"]}))
        self.assertEqual(rc, 2)
        self.assertIn("still IN_PROGRESS", out)
        self.assertFalse(any(p["path"].endswith("media_publish") for p in fake.posts()))

    def test_quota_used_up(self):
        rc, out, fake = self.run_publish("post-image.json", fake=FakeGraph(quota=(50, 50)))
        self.assertEqual(rc, 2)
        self.assertIn("quota used up", out)
        self.assertEqual(fake.posts(), [])

    def test_expired_token_message_is_scrubbed(self):
        rc, out, fake = self.run_publish("post-image.json", fake=FakeGraph(fail={("GET", "me"): 190}))
        self.assertEqual(rc, 2)
        self.assertIn("code 190", out)
        self.assertIn("expired", out)
        self.assertNotIn("TOKEN-SECRET", out)
        self.assertIn("<token>", out)

    def test_explicit_user_id_skips_lookup(self):
        os.environ["IG_USER_ID"] = "999"
        rc, out, fake = self.run_publish("post-image.json")
        self.assertEqual(rc, 0, out)
        self.assertFalse(any(c["path"] == "me" for c in fake.calls))
        self.assertEqual(fake.posts()[0]["path"], "999/media")

    # -- validation ----------------------------------------------------------
    def test_validation_rules(self):
        def ids(post, caption="A fine caption about sourdough starter."):
            return {c["id"]: c["level"] for c in self.m.validate(post, caption, self.ctx)}
        img = lambda u: {"url": u, "kind": "image"}  # noqa: E731
        self.assertEqual(ids({"type": "carousel", "media": [img("https://x.y/a.jpg")]})["shape"], "FAIL")
        self.assertEqual(ids({"type": "carousel", "media": [img("https://x.y/%d.jpg" % i) for i in range(21)]})["shape"], "FAIL")
        self.assertNotIn("shape", ids({"type": "carousel", "media": [img("https://x.y/%d.jpg" % i) for i in range(20)]}))
        self.assertEqual(ids({"type": "reel", "media": [img("https://x.y/a.jpg")]})["shape"], "FAIL")
        self.assertEqual(ids({"type": "image", "media": [img("https://x.y/a.webp")]})["format"], "FAIL")
        self.assertEqual(ids({"type": "image", "media": [img("https://x.y/photo")]})["format"], "WARN")
        self.assertEqual(ids({"type": "image", "media": [img("http://192.168.1.4/a.jpg")]})["url"], "FAIL")
        self.assertEqual(ids({"type": "image", "media": [img("https://x.y/a.jpg")], "extra": 1})["schema"], "FAIL")
        self.assertEqual(ids({"type": "story", "media": [img("https://x.y/a.jpg")]}, "caption")["caption"], "WARN")
        self.assertEqual(ids({"type": "image", "media": [img("https://x.y/a.jpg")]}, "Stop the hustle now.")["gate:banned"], "FAIL")

    def test_story_request(self):
        reqs = self.m.container_requests({"type": "story", "media": [{"url": "https://x.y/v.mp4", "kind": "video"}]}, "")
        self.assertEqual(reqs, [("single", {"media_type": "STORIES", "video_url": "https://x.y/v.mp4"})])

    # -- the network client ----------------------------------------------------
    def test_client_refuses_other_hosts(self):
        with self.assertRaises(self.api.ApiError):
            self.api.Client("t", host="evil.example.com")
        with self.assertRaises(self.api.ApiError):
            self.api.Client("", host="graph.instagram.com")
        c = self.api.Client("t", transport=FakeGraph())
        self.assertTrue(c.base.startswith("https://graph.instagram.com/"))

    def test_check_cli(self):
        r = helpers.run("content-publisher", ["scripts/publish.py", "check", "examples/post-image.json", "--json"])
        out = json.loads(r.stdout)
        self.assertEqual(out["verdict"], "READY")
        self.assertEqual(out["approval_code"], self.code_for("post-image.json"))
        r = helpers.run("content-publisher", ["scripts/publish.py", "check", "examples/post-bad.json", "--json"])
        self.assertEqual(r.returncode, 2)
        self.assertIsNone(json.loads(r.stdout)["approval_code"])


if __name__ == "__main__":
    unittest.main()

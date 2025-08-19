diff --git a/main.py b/main.py
--- a/main.py
+++ b/main.py
@@ -1,5 +1,5 @@
 import asyncio, os, csv, time
-from datetime import datetime, timezone
+from datetime import datetime, timezone
 import httpx
 import pandas as pd
 
@@ -28,6 +28,18 @@
         seen.add(key); unique.append(j)
     return unique
 
+def _as_aware_utc(dt: datetime | None) -> datetime:
+    """
+    Ensure we always return a timezone-aware UTC datetime.
+    - If dt is None -> epoch UTC
+    - If dt is naive -> assume UTC (common for many APIs)
+    - If dt is aware -> convert to UTC
+    """
+    if dt is None:
+        return datetime(1970, 1, 1, tzinfo=timezone.utc)
+    if dt.tzinfo is None:
+        return dt.replace(tzinfo=timezone.utc)
+    return dt.astimezone(timezone.utc)
+
 def write_csv(rows, path):
     os.makedirs(os.path.dirname(path), exist_ok=True)
     with open(path, "w", newline="", encoding="utf-8") as f:
@@ -37,17 +49,20 @@
             w.writerow([
                 j.source, j.job_id, j.title, j.company, j.location, j.url,
                 "|".join(j.tags), (j.description or "").replace("\n"," ")[:1000],
-                j.posted_at.isoformat() if j.posted_at else ""
+                # Always write an aware UTC timestamp (or empty if you prefer epoch -> change next line)
+                (_as_aware_utc(j.posted_at).isoformat() if j.posted_at else "")
             ])
 
 def main():
     jobs = asyncio.run(gather_all())
     relevant = [j for j in jobs if is_relevant(j)]
-    relevant.sort(key=lambda j: (j.posted_at or datetime(1970,1,1, tzinfo=timezone.utc)), reverse=True)
+    # Normalize to aware UTC before sorting to avoid naive/aware comparison TypeError
+    relevant.sort(key=lambda j: _as_aware_utc(j.posted_at), reverse=True)
 
     ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
     latest = "output/latest.csv"
     snapshot = f"output/jobs_{ts}.csv"
 
     write_csv(relevant, latest)
     write_csv(relevant, snapshot)

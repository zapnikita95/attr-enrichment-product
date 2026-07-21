import requests, urllib3, json
urllib3.disable_warnings()
r = requests.post(
  "https://rc1a-q5qd9cc1py7t5c99.mdb.yandexcloud.net:8443",
  auth=("digi-admin","Fl2bSowt"),
  params={"query": """
SELECT
  countIf(location ILIKE '%tsum.ru%') AS loc_tsum,
  countIf(referer ILIKE '%tsum.ru%') AS ref_tsum,
  count() AS total
FROM sessions.searches
WHERE siteId = 203 AND timestamp >= now() - INTERVAL 1 DAY
FORMAT JSON
""", "database":"sessions"},
  timeout=120, verify=False)
print(r.status_code, r.text[:1500])

r2 = requests.post(
  "https://rc1a-q5qd9cc1py7t5c99.mdb.yandexcloud.net:8443",
  auth=("digi-admin","Fl2bSowt"),
  params={"query": """
SELECT location, count() c
FROM sessions.searches
WHERE siteId = 203 AND timestamp >= now() - INTERVAL 1 DAY AND location ILIKE '%tsum%'
GROUP BY location ORDER BY c DESC LIMIT 5
FORMAT JSON
""", "database":"sessions"},
  timeout=120, verify=False)
print(r2.status_code, r2.text[:2000])

#!/usr/bin/env bash
# Chạy kiểm tra trên Facebook giả lập. Dùng: dev/run.sh [tên_test ...]  (không ghi tên: chạy hết)
# Mỗi test in đúng 1 dòng kết quả; log đầy đủ ở dev/work/out_<test>.log
cd "$(dirname "$0")"; export MT_WORK="${MT_WORK:-$PWD/work}"; mkdir -p "$MT_WORK"
[ -d "$MT_WORK/pubimg" ] || cp -r fixtures/pubimg "$MT_WORK/"
ALL="pub_test.py image_test.py link_test.py attach_test.py general_test.py test_images.py mygroups_test.py test_ceo_orders.py test_company.py junk_test.py reset_test.py posted_test.py prospect_test.py policy_test.py site_test.py friends_test.py care_test.py reply_test.py feed_test.py llm_test.py knowledge_test.py groupfit_test.py funnel_test.py focus_test.py preset_test.py learnstats_test.py ceobrain_test.py team_test.py commentall_test.py"
TESTS="${*:-$ALL}"
curl -s -o /dev/null localhost:8098 || { python3 mockfb.py > "$MT_WORK/mockfb.out" 2>&1 & FB=$!; }
curl -s -o /dev/null localhost:8096 || { python3 mockmkt.py > "$MT_WORK/mockmkt.out" 2>&1 & MK=$!; }
for i in $(seq 20); do curl -s -o /dev/null localhost:8098 && break; sleep 0.5; done
for t in $TESTS; do
  t="${t%.py}.py"; timeout 600 python3 "$t" > "$MT_WORK/out_$t.log" 2>&1; ec=$?
  tb=$(grep -c "Traceback" "$MT_WORK/out_$t.log"); echo "$t exit=$ec tb=$tb | $(tail -1 "$MT_WORK/out_$t.log" | cut -c1-120)"
done
[ -n "$FB" ] && kill $FB 2>/dev/null; [ -n "$MK" ] && kill $MK 2>/dev/null; true

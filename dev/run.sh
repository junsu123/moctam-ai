#!/usr/bin/env bash
# Chạy kiểm tra trên Facebook giả lập. Dùng: dev/run.sh [tên_test ...]  (không ghi tên: chạy hết)
# Mỗi test in đúng 1 dòng kết quả; log đầy đủ ở dev/work/out_<test>.log
cd "$(dirname "$0")"; export MT_WORK="${MT_WORK:-$PWD/work}"; mkdir -p "$MT_WORK/multi_shots"
[ -d "$MT_WORK/pubimg" ] || cp -r fixtures/pubimg "$MT_WORK/"
ALL="pub_test.py image_test.py link_test.py attach_test.py general_test.py test_images.py mygroups_test.py test_ceo_orders.py test_company.py junk_test.py reset_test.py posted_test.py prospect_test.py policy_test.py site_test.py deploy_test.py friends_test.py care_test.py reply_test.py feed_test.py llm_test.py knowledge_test.py groupfit_test.py funnel_test.py focus_test.py preset_test.py learnstats_test.py ceobrain_test.py team_test.py commentall_test.py update_test.py housekeeping_test.py coach_test.py comments_test.py bumpwatch_test.py inbox_test.py nickhealth_test.py trendpages_test.py tgimg_test.py pagegrow_test.py"
# QUICK: test không mở Chrome (chạy nhanh, GitHub chạy mỗi lần đẩy code). dev/run.sh quick = chỉ chạy nhóm này.
QUICK="test_images.py test_ceo_orders.py test_company.py reset_test.py posted_test.py policy_test.py site_test.py deploy_test.py llm_test.py knowledge_test.py groupfit_test.py funnel_test.py focus_test.py preset_test.py learnstats_test.py ceobrain_test.py team_test.py commentall_test.py update_test.py housekeeping_test.py coach_test.py comments_test.py bumpwatch_test.py inbox_test.py nickhealth_test.py trendpages_test.py tgimg_test.py"
[ "$1" = "quick" ] && set -- $QUICK
TESTS="${*:-$ALL}"
# Test HỎNG khi: thoát mã khác 0, in "CÓ LỖI a/b" / "KẾT QUẢ: LỖI", hoặc "XONG a/b" với a<b. tb = số Traceback trong log (có test cố ý gây lỗi
# trong luồng nền, nên chỉ để xem, không tính hỏng). Hết danh sách in tổng kết; có test hỏng thì thoát mã 1.
FAILED=""; N=0
curl -s -o /dev/null localhost:8098 || { python3 mockfb.py > "$MT_WORK/mockfb.out" 2>&1 & FB=$!; }
curl -s -o /dev/null localhost:8096 || { python3 mockmkt.py > "$MT_WORK/mockmkt.out" 2>&1 & MK=$!; }
for i in $(seq 20); do curl -s -o /dev/null localhost:8098 && break; sleep 0.5; done
for t in $TESTS; do
  t="${t%.py}.py"; t0=$(date +%s); timeout 600 python3 "$t" > "$MT_WORK/out_$t.log" 2>&1; ec=$?
  tb=$(grep -c "Traceback" "$MT_WORK/out_$t.log"); N=$((N+1))
  xong=$(grep -oE "XONG [0-9]+/[0-9]+" "$MT_WORK/out_$t.log" | tail -1 | awk -F'[ /]' '$2!=$3{print "thiếu"}')
  x=$(grep -cE "^CÓ LỖI [0-9]+/|^KẾT QUẢ: LỖI" "$MT_WORK/out_$t.log")
  st=ok; { [ "$ec" != 0 ] || [ "$x" != 0 ] || [ -n "$xong" ]; } && { st=HỎNG; FAILED="$FAILED $t"; }
  echo "$t $st exit=$ec tb=$tb $(( $(date +%s)-t0 ))s | $(tail -1 "$MT_WORK/out_$t.log" | cut -c1-120)"
  [ "$st" = ok ] || grep -E "✗|Error|LỖI" "$MT_WORK/out_$t.log" | tail -4 | cut -c1-300 | sed 's/^/    > /'
done
[ -n "$FB" ] && kill $FB 2>/dev/null; [ -n "$MK" ] && kill $MK 2>/dev/null
if [ -n "$FAILED" ]; then echo "TỔNG: $(( N-$(echo $FAILED | wc -w) ))/$N đạt. Hỏng:$FAILED (log ở $MT_WORK/out_<test>.log)"; exit 1; fi
echo "TỔNG: $N/$N đạt"

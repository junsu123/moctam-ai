# ------------------------------------------------------------------ Phòng ban: trưởng phòng đánh giá, đề xuất tuyển, CEO xét, nhân viên mới
@app.get("/api/departments")
def depts_get():
    import departments
    return departments.overview()


@app.post("/api/departments/{dept}/review")
def depts_review(dept: str):
    import departments
    if dept not in departments.DEPTS or dept == "director":
        raise HTTPException(400, "Phòng này không có lượt tự đánh giá")
    return departments.review(dept)


@app.post("/api/departments/proposals/{pid}/{action}")
def depts_decide(pid: int, action: str):
    import departments
    try:
        if action == "approve":
            return departments.approve(pid, by="boss")
        if action == "reject":
            return departments.reject(pid)
    except ValueError as e:
        raise HTTPException(400, str(e))
    raise HTTPException(400, "Thao tác không hợp lệ")


@app.post("/api/departments/staff/{sid}/leave")
def depts_staff_leave(sid: int):
    import departments
    try:
        return departments.let_go(sid)
    except ValueError as e:
        raise HTTPException(400, str(e))

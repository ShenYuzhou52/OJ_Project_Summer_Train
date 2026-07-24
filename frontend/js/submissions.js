// ========== 学生提交记录（带分页和筛选） ==========
async function loadMySubmissions(page = 1) {
    const subId = document.getElementById('my-sub-filter-id')?.value.trim() || '';
    const problemId = document.getElementById('my-sub-filter-problem')?.value.trim() || '';
    const status = document.getElementById('my-sub-filter-status')?.value || '';
    const result = document.getElementById('my-sub-filter-result')?.value || '';
    const startTime = document.getElementById('my-sub-filter-start')?.value || '';
    const endTime = document.getElementById('my-sub-filter-end')?.value || '';

    let query = `?page=${page}&page_size=${PAGE_SIZE}`;
    if (subId) query += `&submission_id=${encodeURIComponent(subId)}`;
    if (problemId) query += `&problem_id=${encodeURIComponent(problemId)}`;
    if (status) query += `&status=${encodeURIComponent(status)}`;
    if (result) query += `&result=${encodeURIComponent(result)}`;
    if (startTime) query += `&start_time=${encodeURIComponent(startTime)}`;
    if (endTime) query += `&end_time=${encodeURIComponent(endTime)}`;

    const res = await api('GET', `/api/submissions${query}`);
    if (res.code !== 200) return;
    const list = document.getElementById('submission-list');
    const items = res.data.items;
    const total = res.data.total;
    if (!items || items.length === 0) {
        list.innerHTML = '<div class="empty-state"><p>暂无提交记录</p></div>';
        return;
    }
    let html = items.map(s => `
        <div class="submission-item" onclick="loadSubmissionDetail('${s.id}')">
            <div class="sinfo">
                <div class="sid">${s.problem_id}</div>
                <div class="stime">${s.created_at || ''}</div>
            </div>
            <span class="${statusBadgeClass(s.status)}">${s.status}</span>
            <span class="${resultBadgeClass(s.result)}">${s.result || '-'}</span>
            <span style="font-weight:600; color:#2c3e50; min-width:50px; text-align:right;">${s.score}分</span>
        </div>
    `).join('');
    html += renderPagination(page, total, PAGE_SIZE, 'loadMySubmissions');
    list.innerHTML = html;
}
//向路由发送，获取detail所需的log信息，subRes,logRes,然后组装html
async function loadSubmissionDetail(id) {
    const [subRes, logRes] = await Promise.all([
        api('GET', `/api/submissions/${id}`),
        api('GET', `/api/submissions/${id}/logs`),
    ]);
    if (subRes.code !== 200) { alert(subRes.message); return; }
    const s = subRes.data;

    let html = `
        <div class="card">
            <div class="detail-grid">
                <div class="detail-item"><span class="label">提交编号</span><span class="value">${s.id}</span></div>
                <div class="detail-item"><span class="label">题目</span><span class="value">${s.problem_id}</span></div>
                <div class="detail-item"><span class="label">用户</span><span class="value">${s.user_id || '-'}</span></div>
                <div class="detail-item"><span class="label">状态</span><span class="value"><span class="${statusBadgeClass(s.status)}">${s.status}</span></span></div>
                <div class="detail-item"><span class="label">结果</span><span class="value"><span class="${resultBadgeClass(s.result)}">${s.result || '-'}</span></span></div>
                <div class="detail-item"><span class="label">得分</span><span class="value">${s.score}</span></div>
                <div class="detail-item"><span class="label">总用时</span><span class="value">${s.total_time != null ? s.total_time + 's' : '-'}</span></div>
                <div class="detail-item"><span class="label">提交时间</span><span class="value">${s.created_at || '-'}</span></div>
                <div class="detail-item"><span class="label">开始时间</span><span class="value">${s.started_at || '-'}</span></div>
                <div class="detail-item"><span class="label">结束时间</span><span class="value">${s.finished_at || '-'}</span></div>
                <div class="detail-item"><span class="label">语言</span><span class="value">${s.language || 'python'}</span></div>
            </div>
        </div>
        `;
    

    if (s.source_code) {
        html += `
            <div class="card" style="margin-top:12px;">
                <h3>源代码</h3>
                <pre class="source-code">${escapeHtml(s.source_code)}</pre>
            </div>
        `;
    }

    // 教师/管理员可以重新评测
    if (window._currentUser && (window._currentUser.role === 'teacher' || window._currentUser.role === 'admin')) {
        if (s.status === 'finished' || s.status === 'failed') {
            html += `<div style="margin:12px 0;"><button class="btn-warning" onclick="doRejudge('${s.id}')">重新评测</button></div>`;
        }
    }

    if (logRes.code === 200 && logRes.data && logRes.data.length > 0) {
            html += '<h3 style="margin-top:24px;">测试点详情</h3>';
            for (const log of logRes.data) {
                html += `
                    <div class="case-item">
                        <div class="case-header">
                            <span class="case-id">${log.case_id}</span>
                            <span class="${resultBadgeClass(log.result)}">${log.result}</span>
                            <span style="color:#666; font-size:13px;">${log.score}分 / ${log.time_used}s</span>
                        </div>
                        ${log.message ? '<p style="color:#888; font-size:13px; margin-bottom:8px;">' + escapeHtml(log.message) + '</p>' : ''}
                        ${log.stderr ? '<div style="margin-bottom:8px;"><span style="font-size:12px; color:#888;">标准错误</span><pre>' + escapeHtml(log.stderr) + '</pre></div>' : ''}
                        ${log.stdout !== undefined && log.stdout !== null ? '<div style="margin-bottom:8px;"><span style="font-size:12px; color:#888;">输出</span><pre>' + escapeHtml(log.stdout) + '</pre></div>' : ''}
                        ${log.expected_output !== undefined && log.expected_output !== null ? '<div style="margin-bottom:8px;"><span style="font-size:12px; color:#888;">期望输出</span><pre>' + escapeHtml(log.expected_output) + '</pre></div>' : ''}
                        ${log.input_data !== undefined && log.input_data !== null ? '<div style="margin-bottom:8px;"><span style="font-size:12px; color:#888;">输入</span><pre>' + escapeHtml(log.input_data) + '</pre></div>' : ''}
                    </div>
                `;
            }
        } else if (s.status === 'pending' || s.status === 'running') {
            html += '<div class="empty-state"><p>评测中，请稍后刷新...</p></div>';
            setTimeout(() => loadSubmissionDetail(id), 2000);
        }
    
    document.getElementById('submission-detail').innerHTML = html;
    showPage('submission-detail');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========== 教师提交管理（带分页） ==========
let _teacherSubPage = 1;
async function loadTeacherSubmissions(page = 1) {
    _teacherSubPage = page;
    const subId = document.getElementById('ts-filter-id')?.value.trim() || '';
    const problemId = document.getElementById('ts-filter-problem')?.value.trim() || '';
    const userId = document.getElementById('ts-filter-user')?.value.trim() || '';
    const status = document.getElementById('ts-filter-status')?.value || '';
    const result = document.getElementById('ts-filter-result')?.value || '';
    const startTime = document.getElementById('ts-filter-start')?.value || '';
    const endTime = document.getElementById('ts-filter-end')?.value || '';

    let query = `?page=${page}&page_size=${PAGE_SIZE}`;
    if (subId) query += `&submission_id=${encodeURIComponent(subId)}`;
    if (problemId) query += `&problem_id=${encodeURIComponent(problemId)}`;
    if (userId) query += `&user_id=${encodeURIComponent(userId)}`;
    if (status) query += `&status=${encodeURIComponent(status)}`;
    if (result) query += `&result=${encodeURIComponent(result)}`;
    if (startTime) query += `&start_time=${encodeURIComponent(startTime)}`;
    if (endTime) query += `&end_time=${encodeURIComponent(endTime)}`;

    const res = await api('GET', `/api/submissions${query}`);
    if (res.code !== 200) {
        document.getElementById('teacher-submission-list').innerHTML = '<div class="empty-state"><p>加载失败</p></div>';
        return ;
    }
    const items = res.data.items;
    const total = res.data.total;
    if (!items || items.length === 0) {
        document.getElementById('teacher-submission-list').innerHTML = '<div class="empty-state"><p>暂无提交记录</p></div>';
        return;
    }
    let html = '<table class="user-table"><thead><tr>'
        + '<th>提交编号</th><th>用户</th><th>题目</th><th>状态</th><th>结果</th><th>得分</th><th>时间</th><th>操作</th>'
        + '</tr></thead><tbody>';
    for (const s of items) {
        html += `<tr>
            <td style="font-size:12px;">${s.id.substring(0,8)}...</td>
            <td>${s.user_id.substring(0,8)}...</td>
            <td>${s.problem_id}</td>
            <td><span class="${statusBadgeClass(s.status)}">${s.status}</span></td>
            <td><span class="${resultBadgeClass(s.result)}">${s.result || '-'}</span></td>
            <td>${s.score}</td>
            <td style="font-size:12px;">${s.created_at || ''}</td>
            <td>
                <button class="btn-sm btn-secondary" onclick="loadSubmissionDetail('${s.id}')">详情</button>
                ${(s.status === 'finished' || s.status === 'failed') ? `<button class="btn-sm btn-warning" onclick="doRejudge('${s.id}')">重判</button>` : ''}
            </td>
        </tr>`;
    }
    html += '</tbody></table>';
    html += renderPagination(page, total, PAGE_SIZE, 'loadTeacherSubmissions');
    document.getElementById('teacher-submission-list').innerHTML = html;
}

async function doRejudge(submissionId) {
    if (!confirm('确定要重新评测该提交吗？')) return;
    const res = await api('POST', `/api/submissions/${submissionId}/rejudge`);
    if (res.code === 200) {
        alert('重新评测已启动');
        // 刷新详情
        setTimeout(() => loadSubmissionDetail(submissionId), 1500);
    } else {
        alert('重新评测失败: ' + (res.message || '未知错误'));
    }
}

// ========== 教师日志检索（带分页） ==========
// 缓存日志数据用于详情弹窗
let _teacherLogCache = [];
let _teacherLogPage = 1;

async function loadTeacherLogs(page = 1) {
    _teacherLogPage = page;
    const submissionId = document.getElementById('log-filter-submission')?.value.trim() || '';
    const problemId = document.getElementById('log-filter-problem')?.value.trim() || '';
    const userId = document.getElementById('log-filter-user')?.value.trim() || '';
    const result = document.getElementById('log-filter-result')?.value || '';

    const startTime = document.getElementById('log-filter-start')?.value || '';
    const endTime = document.getElementById('log-filter-end')?.value || '';

    let query = `?page=${page}&page_size=${PAGE_SIZE}`;
    if (submissionId) query += `&submission_id=${encodeURIComponent(submissionId)}`;
    if (problemId) query += `&problem_id=${encodeURIComponent(problemId)}`;
    if (userId) query += `&user_id=${encodeURIComponent(userId)}`;
    if (result) query += `&result=${encodeURIComponent(result)}`;
    if (startTime) query += `&start_time=${encodeURIComponent(startTime)}`;
    if (endTime) query += `&end_time=${encodeURIComponent(endTime)}`;

    const res = await api('GET', `/api/logs${query}`);
    if (res.code !== 200) {
        document.getElementById('teacher-log-list').innerHTML = '<div class="empty-state"><p>加载失败或无权限</p></div>';
        return;
    }
    const items = res.data.items || res.data;
    const total = res.data.total || items.length;
    _teacherLogCache = items;
    if (!items || items.length === 0) {
        document.getElementById('teacher-log-list').innerHTML = '<div class="empty-state"><p>暂无日志</p></div>';
        return;
    }
    // 表头：测试点、提交、结果、得分、用时、创建时间、操作
    let html = '<table class="user-table"><thead><tr>'
        + '<th>测试点</th><th>提交</th><th>结果</th><th>得分</th><th>用时</th><th>创建时间</th><th>操作</th>'
        + '</tr></thead><tbody>';
    for (let i = 0; i < items.length; i++) {
        const log = items[i];
        html += `<tr>
            <td>${log.case_id || '-'}</td>
            <td style="font-size:12px;">${(log.submission_id || '').substring(0,8)}...</td>
            <td><span class="${resultBadgeClass(log.result)}">${log.result || '-'}</span></td>
            <td>${log.score != null ? log.score : '-'}</td>
            <td>${log.time_used != null ? log.time_used + 's' : '-'}</td>
            <td style="font-size:12px;">${log.created_at || '-'}</td>
            <td><button class="btn-sm btn-secondary" onclick="toggleLogDetail(${i}, this)">详情</button></td>
        </tr>
        <tr class="log-detail-row" id="log-detail-row-${i}" style="display:none;">
            <td colspan="7" class="log-detail-cell"></td>
        </tr>`;
    }
    html += '</tbody></table>';
    html += renderPagination(page, total, PAGE_SIZE, 'loadTeacherLogs');
    document.getElementById('teacher-log-list').innerHTML = html;
}

// 测试点日志详情 - 在当前行下方展开显示（完整展示所有字段）
function toggleLogDetail(index, btn) {
    const row = document.getElementById(`log-detail-row-${index}`);
    if (!row) return;
    if (row.style.display !== 'none') {
        row.style.display = 'none';
        btn.textContent = '详情';
        return;
    }
    const log = _teacherLogCache[index];
    if (!log) return;

    // 格式化显示值：null 显示为 "null"，空字符串显示为 (空)
    const fmtVal = (v) => v === null || v === undefined ? 'null' : (v === '' ? '(空)' : String(v));

    let detail = '<div class="log-inline-detail">';
    detail += `<div class="detail-grid">`;
    detail += `<div class="detail-item"><span class="label">submission_id</span><span class="value" style="font-size:12px;word-break:break-all;">${fmtVal(log.submission_id)}</span></div>`;
    detail += `<div class="detail-item"><span class="label">case_id</span><span class="value">${fmtVal(log.case_id)}</span></div>`;
    detail += `<div class="detail-item"><span class="label">result</span><span class="value"><span class="${resultBadgeClass(log.result)}">${fmtVal(log.result)}</span></span></div>`;
    detail += `<div class="detail-item"><span class="label">score</span><span class="value">${fmtVal(log.score)}</span></div>`;
    detail += `<div class="detail-item"><span class="label">time_used</span><span class="value">${log.time_used != null ? log.time_used + 's' : 'null'}</span></div>`;
    detail += `<div class="detail-item"><span class="label">memory_used</span><span class="value">${fmtVal(log.memory_used)}</span></div>`;
    detail += `<div class="detail-item"><span class="label">exit_code</span><span class="value">${fmtVal(log.exit_code)}</span></div>`;
    detail += `<div class="detail-item"><span class="label">is_hidden</span><span class="value">${fmtVal(log.is_hidden)}</span></div>`;
    detail += `<div class="detail-item"><span class="label">created_at</span><span class="value">${fmtVal(log.created_at)}</span></div>`;
    detail += `</div>`;

    // 长文本字段：始终显示，无论是否为空
    detail += `<div style="margin:8px 0;"><span style="font-size:12px; color:#888;">message</span><pre>${escapeHtml(fmtVal(log.message))}</pre></div>`;
    detail += `<div style="margin:8px 0;"><span style="font-size:12px; color:#888;">input_data（输入数据）</span><pre>${escapeHtml(fmtVal(log.input_data))}</pre></div>`;
    detail += `<div style="margin:8px 0;"><span style="font-size:12px; color:#888;">expected_output（标准答案）</span><pre>${escapeHtml(fmtVal(log.expected_output))}</pre></div>`;
    detail += `<div style="margin:8px 0;"><span style="font-size:12px; color:#888;">stdout（实际输出）</span><pre>${escapeHtml(fmtVal(log.stdout))}</pre></div>`;
    detail += `<div style="margin:8px 0;"><span style="font-size:12px; color:#888;">stderr（标准错误）</span><pre>${escapeHtml(fmtVal(log.stderr))}</pre></div>`;

    detail += '</div>';
    row.querySelector('.log-detail-cell').innerHTML = detail;
    row.style.display = '';
    btn.textContent = '收起';
}

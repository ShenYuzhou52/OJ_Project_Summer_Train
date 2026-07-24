// 缓存题目列表，用于前端关键词筛选
let _allProblems = [];

function diffClass(diff) {
    return 'diff-' + (diff || 'easy');
}

function resultBadgeClass(result) {
    const map = { AC: 'ac', WA: 'wa', RE: 're', TLE: 'tle', SE: 'se' };
    return 'badge badge-' + (map[result] || 'pending');
}

function statusBadgeClass(status) {
    return 'badge badge-' + (status || 'pending');
}

let _problemPage = 1;
let _problemSearch = '';

async function loadProblems(searchKeyword = '', page = 1) {
    _problemPage = page;
    _problemSearch = searchKeyword;
    let url = `/api/problems?page=${page}&page_size=${PAGE_SIZE}`;
    if (searchKeyword) {
        url += `&search=${encodeURIComponent(searchKeyword)}`;
    }//拼接url而后交给api
    const res = await api('GET', url);
    if (res.code !== 200) return;
    _allProblems = res.data.items;
    const total = res.data.total;
    renderProblemList(_allProblems, page, total);
    // 1. 清掉"按题目 ID 精确查询"的结果区；
    // 2. 恢复普通题目列表的显示。
    document.getElementById('problem-search-result').innerHTML = '';
    document.getElementById('problem-list').style.display = '';
    // 清空搜索框只在没有搜索关键词时进行
    if (!searchKeyword) {//只有当没搜索时才清空搜索框
        document.getElementById('problem-filter').value = '';
        document.getElementById('problem-search').value = '';
    }
}

// 分页回调（全局函数名供 renderPagination 调用）
function loadProblemsPage(page) {
    loadProblems(_problemSearch, page);
}

function renderProblemList(items, page, total) { //展示数据
    const list = document.getElementById('problem-list');
    if (items.length === 0) {
        list.innerHTML = '<div class="empty-state"><p>暂无题目</p></div>';
        return;
    }
    //把每个题目对象转换成一段 HTML 字符串，最后一次性写入页面
    let html = items.map(p => `
        <div class="problem-item" onclick="loadProblemDetail('${p.id}')">
            <span class="pid">${p.id}</span>
            <span class="ptitle">${p.title}</span>
            <span class="pdiff ${diffClass(p.difficulty)}">${p.difficulty}</span>
            <span class="ptags">${(p.tags || []).join(', ')}</span>
        </div>
    `).join('');
    html += renderPagination(page, total, PAGE_SIZE, 'loadProblemsPage');
    list.innerHTML = html;
}

async function queryProblemById() {
    const searchInput = document.getElementById('problem-search');
    const id = searchInput.value.trim();
    const resultDiv = document.getElementById('problem-search-result');
    const listDiv = document.getElementById('problem-list');
    if (!id) {
        resultDiv.innerHTML = '';
        listDiv.style.display = '';
        return;
    }
    listDiv.style.display = 'none';
    resultDiv.innerHTML = '<p class="search-hint">查询中...</p>';
    const res = await api('GET', `/api/problems/${id}`);
    if (res.code === 200) {
        const p = res.data;
        resultDiv.innerHTML = `
            <div class="problem-item" onclick="loadProblemDetail('${p.id}')">
                <span class="pid">${p.id}</span>
                <span class="ptitle">${p.title}</span>
                <span class="pdiff ${diffClass(p.difficulty)}">${p.difficulty}</span>
                <span class="ptags">${(p.tags || []).join(', ')}</span>
            </div>
        `;
    } else {
        resultDiv.innerHTML = `<p class="search-error">未找到题目 "${id}"（${res.message || 'problem not found'}）</p>`;
    }
}

function filterProblems() {
    const keyword = document.getElementById('problem-filter').value.trim();
    if (!keyword) {
        loadProblems();  // 清空关键词时重新加载所有题目
        return;
    }
    // 使用后端搜索
    loadProblems(keyword);
}

async function loadProblemDetail(id) { //题目详情页并初始化提交区
    const res = await api('GET', `/api/problems/${id}`);
    if (res.code !== 200) { alert(res.message); return; }
    const p = res.data;
    const judgeModeLabel = {standard: '标准比对', strict: '严格比对', spj: 'Special Judge'}[p.judge_mode] || p.judge_mode || '标准比对';
    document.getElementById('problem-title').textContent = `${p.id}: ${p.title}`;
    document.getElementById('problem-desc').innerHTML = `
        <p><strong>描述：</strong>${p.description}</p>
        <p><strong>输入：</strong>${p.input_description}</p>
        <p><strong>输出：</strong>${p.output_description}</p>
        <p><strong>评测模式：</strong><span class="badge badge-judge-mode">${judgeModeLabel}</span></p>
        <p><strong>样例：</strong></p>
        <pre>${(p.samples || []).map(s => '输入: ' + s.input + '\n输出: ' + s.output).join('\n\n')}</pre>
    `;
    document.getElementById('code-input').value = '';
    document.getElementById('submit-result').innerHTML = '';
    window._currentProblemId = id;
    showPage('problem-detail');
}

async function submitCode() {
    const code = document.getElementById('code-input').value;
    if (!code.trim()) { alert('代码不能为空'); return; }
    const lang = document.getElementById('code-language')?.value || 'python'; //就只能是python
    const res = await api('POST', '/api/submissions', {
        problem_id: window._currentProblemId,
        language: lang,
        source_code: code,
    });
    if (res.code === 202) { //202：服务器已经接到任务，但任务还在后台处理。
        document.getElementById('submit-result').innerHTML = `提交成功！提交编号: ${res.data.submission_id}`;
        pollSubmission(res.data.submission_id);
    } else {
        alert(res.message);
    }
}

async function pollSubmission(submissionId) {  //轮询实现
    const check = async () => {
        const res = await api('GET', `/api/submissions/${submissionId}`);
        if (res.code !== 200) return;
        const s = res.data;
        if (s.status === 'pending' || s.status === 'running') {
            // 评测中：显示提交编号和跳转到"我的提交"列表页的链接
            document.getElementById('submit-result').innerHTML = `
                <span class="${statusBadgeClass(s.status)}">${s.status}</span>
                &nbsp; 提交编号: ${s.id}
                &nbsp; 后续结果可至<a href="#" onclick="showPage('submissions'); loadMySubmissions(); return false;" style="color:#2196F3; font-weight:bold;">我的提交</a>查看
            `;
            setTimeout(check, 1000); //setTimeout 会在本次请求完成后再等 1 秒发下一次，不会有请求重叠
        } else {
            // 评测完成：显示状态、结果、得分、用时，并附带跳转到该提交详情页的链接
            document.getElementById('submit-result').innerHTML = `
                <span class="${statusBadgeClass(s.status)}">${s.status}</span>
                <span class="${resultBadgeClass(s.result)}">${s.result || '-'}</span>
                得分: ${s.score} &nbsp; 用时: ${s.total_time || '-'}s
                &nbsp; 详细结果可至<a href="#" onclick="loadSubmissionDetail('${s.id}'); return false;" style="color:#2196F3; font-weight:bold;">我的提交</a>查看
            `;
        }
    };
    check();
}

// ========== 教师/管理员题目管理 ==========

window._problemFormMode = 'create';
window._editingProblemId = null;

let _teacherProblemPage = 1;
let _teacherProblemSearch = '';

async function loadTeacherProblems(searchKeyword = '', page = 1) {
    _teacherProblemPage = page;
    _teacherProblemSearch = searchKeyword;
    let url = `/api/problems?page=${page}&page_size=${PAGE_SIZE}`;
    if (searchKeyword) {
        url += `&search=${encodeURIComponent(searchKeyword)}`;
    }
    const res = await api('GET', url);
    if (res.code !== 200) return;
    const list = document.getElementById('teacher-problem-list');
    const items = res.data.items;
    const total = res.data.total;
    if (items.length === 0) {
        list.innerHTML = '<div class="empty-state"><p>暂无题目</p></div>';
        return;
    }
    let html = items.map(p => `
        <div class="problem-item">
            <span class="pid">${p.id}</span>
            <span class="ptitle">${p.title}</span>
            <span class="pdiff ${diffClass(p.difficulty)}">${p.difficulty}</span>
            <div class="action-btns">
                <button class="btn-warning" onclick="editProblem('${p.id}')">编辑</button>
                <button class="btn-danger" onclick="deleteProblem('${p.id}')">删除</button>
            </div>
        </div>
    `).join('');
    html += renderPagination(page, total, PAGE_SIZE, 'loadTeacherProblemsPage');
    list.innerHTML = html;
}

// 教师题目管理分页回调
function loadTeacherProblemsPage(page) {
    loadTeacherProblems(_teacherProblemSearch, page);
}

function showCreateProblem() {
    window._problemFormMode = 'create';
    window._editingProblemId = null;
    document.getElementById('problem-form-title').textContent = '创建题目';
    document.getElementById('pf-id').value = '';
    document.getElementById('pf-id').disabled = false;
    document.getElementById('pf-title').value = '';
    document.getElementById('pf-description').value = '';
    document.getElementById('pf-input-desc').value = '';
    document.getElementById('pf-output-desc').value = '';
    document.getElementById('pf-samples').value = '[{"input": "1 2\\n", "output": "3\\n"}]';
    document.getElementById('pf-constraints').value = '';
    document.getElementById('pf-time-limit').value = '1.0';
    document.getElementById('pf-memory-limit').value = '128';
    document.getElementById('pf-difficulty').value = 'easy';
    document.getElementById('pf-tags').value = '';
    document.getElementById('pf-test-cases').value = '[{"case_id":"case_01","input":"1 2\\n","output":"3\\n","score":50,"is_hidden":false},{"case_id":"case_02","input":"-1 2\\n","output":"1\\n","score":50,"is_hidden":true}]';
    document.getElementById('pf-judge-mode').value = 'standard';
    document.getElementById('pf-spj-code').value = '';
    toggleSpjField();
    document.getElementById('pf-error').textContent = '';
    showPage('problem-form');
}

async function editProblem(id) {
    const res = await api('GET', `/api/problems/${id}`);
    if (res.code !== 200) { alert(res.message); return; }
    const p = res.data;
    window._problemFormMode = 'edit';
    window._editingProblemId = id;
    document.getElementById('problem-form-title').textContent = '编辑题目: ' + id;
    document.getElementById('pf-id').value = p.id;
    document.getElementById('pf-id').disabled = true;
    document.getElementById('pf-title').value = p.title;
    document.getElementById('pf-description').value = p.description;
    document.getElementById('pf-input-desc').value = p.input_description;
    document.getElementById('pf-output-desc').value = p.output_description;
    document.getElementById('pf-samples').value = JSON.stringify(p.samples || [], null, 2);
    document.getElementById('pf-constraints').value = p.constraints || '';
    document.getElementById('pf-time-limit').value = p.time_limit;
    document.getElementById('pf-memory-limit').value = p.memory_limit;
    document.getElementById('pf-difficulty').value = p.difficulty;
    document.getElementById('pf-tags').value = (p.tags || []).join(', ');
    document.getElementById('pf-test-cases').value = JSON.stringify(p.test_cases || [], null, 2);
    document.getElementById('pf-judge-mode').value = p.judge_mode || 'standard';
    document.getElementById('pf-spj-code').value = p.spj_code || '';
    toggleSpjField();
    document.getElementById('pf-error').textContent = '';
    showPage('problem-form');
}

async function deleteProblem(id) {
    if (!confirm(`确定要删除题目 ${id} 吗？`)) return;
    const res = await api('DELETE', `/api/problems/${id}`); //调用api，告知后端要执行删除操作，后端返回res
    if (res.code === 200) {
        alert('删除成功');
        loadTeacherProblems(); //重载
    } else {
        alert('删除失败: ' + res.message);
    }
}

function filterTeacherProblems() { 
    const keyword = document.getElementById('teacher-problem-filter').value.trim();//从前端dom抓取
    loadTeacherProblems(keyword);
}

async function saveProblem() {
    const errorEl = document.getElementById('pf-error');
    errorEl.textContent = '';

    let samples, testCases;
    try {
        samples = JSON.parse(document.getElementById('pf-samples').value);
    } catch (e) {
        errorEl.textContent = '样例格式错误，请输入有效的JSON数组';
        return;
    }
    try {
        testCases = JSON.parse(document.getElementById('pf-test-cases').value);
    } catch (e) {
        errorEl.textContent = '测试点格式错误，请输入有效的JSON数组';
        return;
    }

    const tagsStr = document.getElementById('pf-tags').value.trim();
    const tags = tagsStr ? tagsStr.split(',').map(t => t.trim()).filter(t => t) : [];

    const judgeMode = document.getElementById('pf-judge-mode').value;
    const spjCode = document.getElementById('pf-spj-code').value;

    const body = {
        id: document.getElementById('pf-id').value.trim(),
        title: document.getElementById('pf-title').value.trim(),
        description: document.getElementById('pf-description').value,
        input_description: document.getElementById('pf-input-desc').value,
        output_description: document.getElementById('pf-output-desc').value,
        samples: samples,
        constraints: document.getElementById('pf-constraints').value,
        time_limit: parseFloat(document.getElementById('pf-time-limit').value),
        memory_limit: parseFloat(document.getElementById('pf-memory-limit').value),
        difficulty: document.getElementById('pf-difficulty').value,
        tags: tags,
        test_cases: testCases,
        judge_mode: judgeMode,
    };
    if (judgeMode === 'spj') {
        body.spj_code = spjCode;
    }

    try {
        let res;
        if (window._problemFormMode === 'create') {
            res = await api('POST', '/api/problems', body);
        } else {
            delete body.id;
            res = await api('PUT', `/api/problems/${window._editingProblemId}`, body);
        }

        if (res.detail) {
            const msgs = Array.isArray(res.detail)
                ? res.detail.map(d => d.msg || String(d)).join('; ')
                : String(res.detail);
            errorEl.textContent = '错误: ' + msgs;
            return;
        }

        if (res.code === 201 || res.code === 200) {
            alert(window._problemFormMode === 'create' ? '创建成功' : '修改成功');
            showPage('teacher');
            loadTeacherProblems();
        } else {
            errorEl.textContent = res.message || JSON.stringify(res) || '操作失败';
        }
    } catch (e) {
        console.error('saveProblem error:', e);
        errorEl.textContent = '请求失败: ' + e.message;
    }
}

// ========== Judge Mode / SPJ 辅助 ==========

function toggleSpjField() {
    const mode = document.getElementById('pf-judge-mode').value;
    const spjGroup = document.getElementById('spj-code-group');
    if (spjGroup) {
        // 是 SPJ 模式则显示 SPJ 代码输入区域；否则隐藏。
        spjGroup.style.display = mode === 'spj' ? '' : 'none';
    }
}

// ========== 代码相似度检测 ==========

async function runSimilarityCheck() {
    const problemId = document.getElementById('sim-problem-id').value.trim();
    const idsStr = document.getElementById('sim-submission-ids').value.trim();
    const resultDiv = document.getElementById('sim-result');

    if (!problemId) { alert('请输入题目ID'); return; }
    if (!idsStr) { alert('请输入提交ID列表'); return; }

    const submissionIds = idsStr.split(/[\s,;]+/).filter(s => s);
    if (submissionIds.length < 2) { alert('至少输入2个提交ID'); return; }

    resultDiv.innerHTML = '<p>检测中...</p>';

    const res = await api('POST', `/api/problems/${problemId}/similarity-check`, {
        submission_ids: submissionIds,
    });

    if (res.code !== 200) {
        resultDiv.innerHTML = `<p class="search-error">错误: ${res.message}</p>`;
        return;
    }

    renderSimilarityReport(res.data, resultDiv);
}

async function loadSimilarityReports() {
    const problemId = document.getElementById('sim-problem-id').value.trim();
    const resultDiv = document.getElementById('sim-result');
    if (!problemId) { alert('请输入题目ID'); return; }

    resultDiv.innerHTML = '<p>加载中...</p>';
    const res = await api('GET', `/api/problems/${problemId}/similarity-reports`);
    if (res.code !== 200) {
        resultDiv.innerHTML = `<p class="search-error">错误: ${res.message}</p>`;
        return;
    }
    renderSimilarityReport(res.data, resultDiv);
}

// 缓存相似度报告数据用于详情展开
let _similarityReportCache = [];

function renderSimilarityReport(data, container) {
    if (!data.reports || data.reports.length === 0) {
        container.innerHTML = '<p>暂无报告</p>';
        return;
    }

    _similarityReportCache = data.reports;
    const threshold = data.threshold || 0.9;
    let html = `<p>题目: ${data.problem_id} | 总对数: ${data.total_pairs} | 超阈值(${threshold}): <strong>${data.flagged_pairs}</strong></p>`;
    html += '<table class="sim-table"><thead><tr><th>提交A</th><th>提交B</th><th>相似度</th><th>方法</th><th>时间</th><th>状态</th><th>操作</th></tr></thead><tbody>';

    for (let i = 0; i < data.reports.length; i++) {
        const r = data.reports[i];
        const flagged = r.above_threshold;
        const rowClass = flagged ? 'sim-flagged' : '';
        const statusText = flagged ? '⚠️ 疑似相似' : '正常';
        html += `<tr class="${rowClass}">
            <td title="${r.submission_a}">${r.submission_a.substring(0, 8)}...</td>
            <td title="${r.submission_b}">${r.submission_b.substring(0, 8)}...</td>
            <td><strong>${(r.similarity * 100).toFixed(1)}%</strong></td>
            <td>${r.method}</td>
            <td>${r.created_at ? r.created_at.substring(0, 19) : '-'}</td>
            <td>${statusText}</td>
            <td><button class="btn-sm btn-secondary" onclick="toggleSimDetail(${i}, this)">显示详情</button></td>
        </tr>
        <tr class="sim-detail-row" id="sim-detail-row-${i}" style="display:none;">
            <td colspan="7" class="sim-detail-cell"></td>
        </tr>`;
    }
    html += '</tbody></table>';
    container.innerHTML = html;
}

// 切换相似度报告详情显示
function toggleSimDetail(index, btn) {
    const row = document.getElementById(`sim-detail-row-${index}`);
    if (!row) return;
    if (row.style.display !== 'none') {
        row.style.display = 'none';
        btn.textContent = '显示详情';
        return;
    }
    const report = _similarityReportCache[index];
    if (!report) return;
    row.querySelector('.sim-detail-cell').innerHTML =
        '<pre class="sim-detail-json">' + escapeHtml(JSON.stringify(report, null, 2)) + '</pre>';
    row.style.display = '';
    btn.textContent = '隐藏详情';
}

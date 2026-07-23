const API_BASE = '';  // 同源
//document作为浏览器提供的全局对象，代表整个文档（html文件）
function showPage(pageId) {
    // 根据元素的 id 精确查找一个 DOM 元素
    document.querySelectorAll('[id^="page-"]').forEach(el => el.style.display = 'none');
    // 查找id = page- + pageID 的元素
    const page = document.getElementById('page-' + pageId);
    if (page) page.style.display = '';//清空该元素的内联 display 样式，使其恢复 CSS 默认规则
}

async function api(method, path, body = null) {
     // 构造 fetch 请求配置对象。
    const opts = {
        method, //HTTP方法
        headers: { 'Content-Type': 'application/json' },// 告诉后端请求体内容采用 JSON 格式。
        credentials: 'include',// 请求时携带 Cookie、Session 等身份凭据。
    };
    // 如果调用方传入了 body，则把 JavaScript 对象转换为 JSON 字符串。
    if (body) opts.body = JSON.stringify(body);
    try {
        const resp = await fetch(API_BASE + path, opts);//fetch() 用于发起 HTTP 请求。请求完成后继续执行
        const data = await resp.json();
        // 如果后端返回的是 HTTPException 格式 (FastAPI默认 {detail: ...})，统一转换
        if (data.detail !== undefined && data.code === undefined) {
            const msg = typeof data.detail === 'string' ? data.detail :
                (Array.isArray(data.detail) ? data.detail.map(d => d.msg || String(d)).join('; ') : JSON.stringify(data.detail));
            // 统一转换为项目中的错误返回结构。
            return { code: resp.status, message: msg };
        }
        return data;
    } catch (e) {
        console.error('API error:', e);
        return { code: 0, message: '网络错误或服务器无响应' };
    }
}

// 全局用户状态
window._currentUser = null;

// 根据角色显示/隐藏管理入口
function updateNavByRole(role) {
    const teacherLink = document.getElementById('teacher-link');
    const teacherSubLink = document.getElementById('teacher-sub-link');
    const teacherLogLink = document.getElementById('teacher-log-link');
    const adminLink = document.getElementById('admin-link');
    const profileLink = document.getElementById('profile-link');

    // 登录后都显示修改密码
    if (profileLink) profileLink.style.display = 'inline';

    // 登录后显示我的提交导航
    const submissionsLink = document.getElementById('submissions-link');
    if (submissionsLink) submissionsLink.style.display = 'inline';

    const similarityLink = document.getElementById('similarity-link');

    if (role === 'teacher' || role === 'admin') {
        teacherLink.style.display = 'inline';
        teacherSubLink.style.display = 'inline';
        teacherLogLink.style.display = 'inline';
        if (similarityLink) similarityLink.style.display = 'inline';
    } else {
        teacherLink.style.display = 'none';
        teacherSubLink.style.display = 'none';
        teacherLogLink.style.display = 'none';
        if (similarityLink) similarityLink.style.display = 'none';
    }
    if (role === 'admin') {
        adminLink.style.display = 'inline';
    } else {
        adminLink.style.display = 'none';
    }
}

// ========== 分页组件 ==========
const PAGE_SIZE = 20;

/**
 * 渲染分页控件的 HTML
 * @param {number} page 当前页码
 * @param {number} total 总条数
 * @param {number} pageSize 每页条数
 * @param {string} onPageChange 全局回调函数名，如 "loadMySubmissionsPage"
 */
function renderPagination(page, total, pageSize, onPageChange) {
    const totalPages = Math.ceil(total / pageSize);
    if (totalPages <= 1) return '';
    let html = '<div class="pagination">';
    if (page > 1) html += `<button class="btn-sm btn-secondary" onclick="${onPageChange}(${page - 1})">上一页</button>`;
    html += `<span class="page-info">${page} / ${totalPages} (共 ${total} 条)</span>`;
    if (page < totalPages) html += `<button class="btn-sm btn-secondary" onclick="${onPageChange}(${page + 1})">下一页</button>`;
    html += '</div>';
    return html;
}

// ========== 详情弹窗（展示完整 JSON） ==========
function showDetailModal(title, jsonObj) {
    // 移除旧弹窗
    const old = document.getElementById('detail-modal-overlay');
    if (old) old.remove();

    const overlay = document.createElement('div');
    overlay.id = 'detail-modal-overlay';
    overlay.className = 'modal-overlay';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    const content = document.createElement('div');
    content.className = 'modal-content';
    content.innerHTML = `
        <div class="modal-header">
            <h3>${title}</h3>
            <button class="btn-sm btn-secondary" onclick="document.getElementById('detail-modal-overlay').remove()">✕</button>
        </div>
        <pre class="modal-json">${escapeHtml(JSON.stringify(jsonObj, null, 2))}</pre>
    `;
    overlay.appendChild(content);
    document.body.appendChild(overlay);
}

// 页面加载时检查登录状态
window.addEventListener('load', async () => {
    // 获取当前已登录用户的用户名、角色等资料。
    const res = await api('GET', '/api/auth/me');
    if (res.code === 200) {
        window._currentUser = res.data;
        // textContent直接在前端演示的
        document.getElementById('user-info').textContent = `${res.data.username} (${res.data.role})`;
        document.getElementById('login-link').style.display = 'none';
        document.getElementById('logout-link').style.display = 'inline';
        updateNavByRole(res.data.role);
        showPage('problems');
        loadProblems();
    } else {
        // 未登录时显示登录页
        showPage('login');
    }
});

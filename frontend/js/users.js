// ========== 用户管理 - 仅 admin ==========

let _userPage = 1;

async function loadUsers(page = 1) {
    _userPage = page;
    const filterUsername = document.getElementById('user-filter-username')?.value.trim() || '';
    const filterRole = document.getElementById('user-filter-role')?.value || '';
    const filterStatus = document.getElementById('user-filter-status')?.value || '';

    let query = `?page=${page}&page_size=20`;
    if (filterUsername) query += `&username=${encodeURIComponent(filterUsername)}`;
    if (filterRole) query += `&role=${encodeURIComponent(filterRole)}`;
    if (filterStatus) query += `&is_active=${filterStatus === 'active' ? 'true' : 'false'}`;

    const res = await api('GET', `/api/users${query}`);
    if (res.code !== 200) {
        document.getElementById('user-list').innerHTML = '<div class="empty-state"><p>无权限访问</p></div>';
        return;
    }
    const { items, total, page_size } = res.data;
    const totalPages = Math.ceil(total / page_size);

    let html = '';
    if (items.length === 0) {
        html = '<div class="empty-state"><p>暂无用户</p></div>';
    } else {
        html = '<table class="user-table"><thead><tr>'
            + '<th>用户名</th><th>角色</th><th>状态</th><th>创建时间</th><th>操作</th>'
            + '</tr></thead><tbody>';
        for (const u of items) {
            const statusText = u.is_active ? '启用' : '禁用';
            const statusClass = u.is_active ? 'badge-ac' : 'badge-wa';
            html += `<tr>
                <td class="uname">${u.username}</td>
                <td><span class="badge ${roleBadgeClass(u.role)}">${u.role}</span></td>
                <td><span class="badge ${statusClass}">${statusText}</span></td>
                <td class="utime">${u.created_at || '-'}</td>
                <td class="uaction">
                    <select id="role-${u.id}" onchange="updateUserRole('${u.id}', this.value)">
                        <option value="student" ${u.role === 'student' ? 'selected' : ''}>student</option>
                        <option value="teacher" ${u.role === 'teacher' ? 'selected' : ''}>teacher</option>
                        <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>admin</option>
                    </select>
                    <button class="btn-sm ${u.is_active ? 'btn-danger' : 'btn-success'}" 
                        onclick="toggleUserActive('${u.id}', ${!u.is_active})">
                        ${u.is_active ? '禁用' : '启用'}
                    </button>
                    <button class="btn-sm btn-warning" onclick="resetUserPassword('${u.id}', '${u.username}')">重置密码</button>
                </td>
            </tr>`;
        }
        html += '</tbody></table>';
        if (totalPages > 1) {
            html += '<div class="pagination">';
            if (page > 1) html += `<button class="btn-sm btn-secondary" onclick="loadUsers(${page - 1})">上一页</button>`;
            html += `<span class="page-info">${page} / ${totalPages} (共 ${total} 人)</span>`;
            if (page < totalPages) html += `<button class="btn-sm btn-secondary" onclick="loadUsers(${page + 1})">下一页</button>`;
            html += '</div>';
        }
    }
    document.getElementById('user-list').innerHTML = html;
}

function roleBadgeClass(role) {
    const map = { admin: 'badge-se', teacher: 'badge-running', student: 'badge-ac' };
    return map[role] || 'badge-pending';
}

async function updateUserRole(userId, newRole) {
    const res = await api('PUT', `/api/users/${userId}`, { role: newRole });
    if (res.code === 200) {
        loadUsers(_userPage);
    } else {
        alert('修改角色失败: ' + (res.message || '未知错误'));
        loadUsers(_userPage);
    }
}

async function toggleUserActive(userId, isActive) {
    const action = isActive ? '启用' : '禁用';
    if (!confirm(`确定要${action}该用户吗？`)) return;
    const res = await api('PUT', `/api/users/${userId}`, { is_active: isActive });
    if (res.code === 200) {
        loadUsers(_userPage);
    } else {
        alert(`${action}失败: ` + (res.message || '未知错误'));
        loadUsers(_userPage);
    }
}

async function resetUserPassword(userId, username) {
    const newPwd = prompt(`请输入用户 "${username}" 的新密码（至少8字符）：`);
    if (!newPwd) return;
    if (newPwd.length < 8) {
        alert('密码长度至少8个字符');
        return;
    }
    const res = await api('POST', `/api/users/${userId}/reset-password`, { new_password: newPwd });
    if (res.code === 200) {
        alert('密码重置成功');
    } else {
        alert('密码重置失败: ' + (res.message || '未知错误'));
    }
}

// ========== 备份管理 - 仅 admin ==========

async function loadBackups() {
    const res = await api('GET', '/api/admin/backups');
    if (res.code !== 200) {
        document.getElementById('backup-list').innerHTML = '<div class="empty-state"><p>加载失败或无权限</p></div>';
        return;
    }
    const backups = res.data;
    if (!backups || backups.length === 0) {
        document.getElementById('backup-list').innerHTML = '<div class="empty-state"><p>暂无备份</p></div>';
        return;
    }
    let html = '<table class="user-table"><thead><tr>'
        + '<th>备份ID</th><th>创建时间</th><th>操作</th>'
        + '</tr></thead><tbody>';
    for (const b of backups) {
        html += `<tr>
            <td>${b.backup_id || b.id || '-'}</td>
            <td>${b.created_at || '-'}</td>
            <td><button class="btn-sm btn-warning" onclick="doRestore('${b.backup_id || b.id}')">恢复</button></td>
        </tr>`;
    }
    html += '</tbody></table>';
    document.getElementById('backup-list').innerHTML = html;
}

async function doCreateBackup() { //创建备份，而不是开始
    const res = await api('POST', '/api/admin/backups');
    if (res.code === 201 || res.code === 200) {
        alert('备份创建成功');
        loadBackups();
    } else {
        alert('备份创建失败: ' + (res.message || '未知错误'));
    }
}

async function doRestore(backupId) {
    if (!confirm(`确定要从备份 ${backupId} 恢复数据吗？\n恢复后当前数据将被覆盖，Session可能失效。`)) return;
    const res = await api('POST', `/api/admin/backups/${backupId}/restore`);
    if (res.code === 200) {
        alert('恢复成功！页面将刷新。');
        location.reload();
    } else {
        alert('恢复失败: ' + (res.message || '未知错误'));
    }
}

// ========== 审计日志 - 仅 admin（带分页和详情弹窗） ==========

// 缓存审计日志数据用于详情弹窗
let _auditLogCache = [];
let _auditLogPage = 1;

async function loadAuditLogs(page = 1) {
    _auditLogPage = page;
    const action = document.getElementById('audit-filter-action')?.value.trim() || '';
    const operatorId = document.getElementById('audit-filter-operator')?.value.trim() || '';
    const targetId = document.getElementById('audit-filter-target')?.value.trim() || '';

    const startTime = document.getElementById('audit-filter-start')?.value || '';
    const endTime = document.getElementById('audit-filter-end')?.value || '';

    let query = `?page=${page}&page_size=${PAGE_SIZE}`;
    if (action) query += `&action=${encodeURIComponent(action)}`;
    if (operatorId) query += `&operator_id=${encodeURIComponent(operatorId)}`;
    if (targetId) query += `&target_id=${encodeURIComponent(targetId)}`;
    if (startTime) query += `&start_time=${encodeURIComponent(startTime)}`;
    if (endTime) query += `&end_time=${encodeURIComponent(endTime)}`;

    const res = await api('GET', `/api/audit-logs${query}`);
    if (res.code !== 200) {
        document.getElementById('audit-log-list').innerHTML = '<div class="empty-state"><p>加载失败或无权限</p></div>';
        return;
    }
    const items = res.data.items || res.data;
    const total = res.data.total || items.length;
    _auditLogCache = items;
    if (!items || items.length === 0) {
        document.getElementById('audit-log-list').innerHTML = '<div class="empty-state"><p>暂无审计日志</p></div>';
        return;
    }
    let html = '<table class="user-table"><thead><tr>'
        + '<th>时间</th><th>操作者</th><th>操作</th><th>目标类型</th><th>目标ID</th><th>操作</th>'
        + '</tr></thead><tbody>';
    for (let i = 0; i < items.length; i++) {
        const log = items[i];
        html += `<tr>
            <td style="font-size:12px;">${log.created_at || log.timestamp || '-'}</td>
            <td style="font-size:12px;">${(log.operator_id || '').substring(0,8)}...</td>
            <td>${log.action || '-'}</td>
            <td>${log.target_type || '-'}</td>
            <td style="font-size:12px;">${(log.target_id || '').substring(0,8)}...</td>
            <td><button class="btn-sm btn-secondary" onclick="toggleAuditLogDetail(${i}, this)">详情</button></td>
        </tr>
        <tr class="log-detail-row" id="audit-log-detail-row-${i}" style="display:none;">
            <td colspan="6" class="log-detail-cell"></td>
        </tr>`;
    }
    html += '</tbody></table>';
    html += renderPagination(page, total, PAGE_SIZE, 'loadAuditLogs');
    document.getElementById('audit-log-list').innerHTML = html;
}

// 审计日志详情 - 在当前行下方展开显示完整 JSON
function toggleAuditLogDetail(index, btn) {
    const row = document.getElementById(`audit-log-detail-row-${index}`);
    if (!row) return;
    if (row.style.display !== 'none') {
        row.style.display = 'none';
        btn.textContent = '详情';
        return;
    }
    const log = _auditLogCache[index];
    if (!log) return;
    let detail = '<div class="log-inline-detail">';
    detail += '<pre class="modal-json">' + JSON.stringify(log, null, 2) + '</pre>';
    detail += '</div>';
    row.querySelector('.log-detail-cell').innerHTML = detail;
    row.style.display = '';
    btn.textContent = '收起';
}

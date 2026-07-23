let _authErrorTimer = null;

async function doLogin() {
    const username = document.getElementById('login-username').value.trim();//移除前后空白字符
    const password = document.getElementById('login-password').value;
    if (!username || !password) {
        showAuthError('login', '请输入用户名和密码');
        return;
    }
    clearAuthError('login');
    const res = await api('POST', '/api/auth/login', { username, password });
    if (res.code === 200) {  //登录成功，进入网站内部页
        window._currentUser = res.data;
        document.getElementById('user-info').textContent = `${res.data.username} (${res.data.role})`;
        document.getElementById('login-link').style.display = 'none';
        document.getElementById('logout-link').style.display = 'inline';
        updateNavByRole(res.data.role);
        showPage('problems');
        loadProblems();
    } else {
        showAuthError('login', res.message || '登录失败');
    }
}

async function doRegister() {
    const username = document.getElementById('reg-username').value.trim();
    const password = document.getElementById('reg-password').value;
    if (!username || !password) {
        showAuthError('register', '请输入用户名和密码');
        return;
    }
    clearAuthError('register');
    // 向后端发送注册请求；请求方法：POST；请求地址：/api/auth/register
    const res = await api('POST', '/api/auth/register', { username, password });
    if (res.code === 201) {
        alert('注册成功，请登录');
        showPage('login');
    } else {
        showAuthError('register', res.message || '注册失败');
    }
}

async function logout() {
    await api('POST', '/api/auth/logout');
    window._currentUser = null;
    document.getElementById('user-info').textContent = '';
    document.getElementById('login-link').style.display = 'inline';
    document.getElementById('logout-link').style.display = 'none';
    document.getElementById('teacher-link').style.display = 'none';
    document.getElementById('teacher-sub-link').style.display = 'none';
    document.getElementById('teacher-log-link').style.display = 'none';
    document.getElementById('admin-link').style.display = 'none';
    const simLink = document.getElementById('similarity-link');
    if (simLink) simLink.style.display = 'none';
    const profileLink = document.getElementById('profile-link');
    if (profileLink) profileLink.style.display = 'none';
    // 隐藏需要登录才能看到的导航
    const submissionsLink = document.getElementById('submissions-link');
    if (submissionsLink) submissionsLink.style.display = 'none';
    // 登出后回到登录页
    showPage('login');
}

// 修改密码
async function doChangePassword() {
    const errorEl = document.getElementById('cp-error');
    errorEl.textContent = '';
    const oldPwd = document.getElementById('cp-old-password').value;
    const newPwd = document.getElementById('cp-new-password').value;
    const confirmPwd = document.getElementById('cp-confirm-password').value;

    if (!oldPwd || !newPwd || !confirmPwd) {
        errorEl.textContent = '请填写所有字段';
        return;
    }
    if (newPwd.length < 8) {
        errorEl.textContent = '新密码至少8个字符';
        return;
    }
    if (newPwd !== confirmPwd) {
        errorEl.textContent = '两次输入的新密码不一致';
        return;
    }

    const res = await api('POST', '/api/auth/change-password', {
        old_password: oldPwd,
        new_password: newPwd,
    });

    if (res.code === 200) {
        alert('密码修改成功');
        // 密码不应长期保留在页面输入框中。
        document.getElementById('cp-old-password').value = '';
        document.getElementById('cp-new-password').value = '';
        document.getElementById('cp-confirm-password').value = '';
        //错误提示区为空
        errorEl.textContent = '';
    } else {
        errorEl.textContent = res.message || '修改失败';
    }
}

function showAuthError(page, message) {
    clearAuthError(page);
    const card = document.querySelector('#page-' + page + ' .auth-card');
    if (!card) return;
    let errEl = card.querySelector('.auth-error');
    if (!errEl) {
        errEl = document.createElement('div');//在 JavaScript 中创建新的 DOM 元素
        errEl.className = 'auth-error';
        card.insertBefore(errEl, card.querySelector('.btn-row'));// 将 errEl 插入到 .btn-row 元素之前，最终效果是错误信息显示在按钮上方
    }
    errEl.textContent = message;
    // setTimeout(callback, delay)，在指定毫秒后执行一次 callback。返回的是一个定时器id
    _authErrorTimer = setTimeout(() => {
        clearAuthError(page);//4秒后clear
        _authErrorTimer = null;// 定时器已经执行完毕，将全局变量恢复为 null
    }, 4000);
}

function clearAuthError(page) {
    if (_authErrorTimer) {
        clearTimeout(_authErrorTimer);// 取消由 setTimeout() 创建、但尚未执行的定时器。
        _authErrorTimer = null;// 清空id
    }
    // 查找 id="page-login" 元素内部，class="auth-card" 的第一个元素。
    const card = document.querySelector('#page-' + page + ' .auth-card');
    if (!card) return;
    const errEl = card.querySelector('.auth-error');
    if (errEl) errEl.textContent = '';
}

document.addEventListener('DOMContentLoaded', () => {
    ['login-username', 'login-password'].forEach(id => {
        const el = document.getElementById(id); 
        // 用户一旦重新编辑登录用户名或密码，就立即清除原本显示的登录错误提示，页面更自然
        if (el) el.addEventListener('input', () => clearAuthError('login')); //给元素绑定监听器
    });
    ['reg-username', 'reg-password'].forEach(id => { //每个都处理
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', () => clearAuthError('register'));
    });
});
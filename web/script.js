// ==========================================
// Haiku Fishing - Frontend Script
// ==========================================

// ---- Tab Navigation ----
function switchTab(tabName) {
    // Deactivate all pages and nav items
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    // Activate selected
    const page = document.getElementById(tabName);
    if (page) page.classList.add('active');

    const navItem = document.querySelector(`.nav-item[data-tab="${tabName}"]`);
    if (navItem) navItem.classList.add('active');

    // Reset advanced warning
    if (tabName === 'advanced') {
        const banner = document.getElementById('warningBanner');
        const content = document.getElementById('advancedContent');
        const header = document.getElementById('advancedHeader');
        if (banner) banner.style.display = '';
        if (content) content.style.display = 'none';
        if (header) header.style.display = 'none';
    }
}

// ---- Collapse Sections ----
function toggleCollapse(arrowEl) {
    arrowEl.classList.toggle('collapsed');
    const section = arrowEl.closest('.section');
    if (section) {
        const content = section.querySelector('.section-content');
        if (content) content.classList.toggle('collapsed');
    }
}

function setSectionCollapse(sectionId, collapsed) {
    const content = document.getElementById(sectionId);
    if (!content) return;
    // Sync the collapse arrow too
    const section = content.closest('.section');
    const arrow = section ? section.querySelector('.collapse-arrow') : null;
    if (collapsed) {
        content.classList.add('collapsed');
        if (arrow) arrow.classList.add('collapsed');
    } else {
        content.classList.remove('collapsed');
        if (arrow) arrow.classList.remove('collapsed');
    }
}

// ---- Advanced Warning ----
function goBack() {
    switchTab('main');
}

function proceedAdvanced() {
    const banner = document.getElementById('warningBanner');
    const content = document.getElementById('advancedContent');
    const header = document.getElementById('advancedHeader');
    if (banner) banner.style.display = 'none';
    if (content) content.style.display = 'block';
    if (header) header.style.display = '';
}

// ---- Toast Notifications ----
function showToast(title, message, type) {
    type = type || 'success';
    const toast = document.getElementById('toast');
    if (!toast) return;

    const iconEl = toast.querySelector('.toast-icon');
    const titleEl = toast.querySelector('.toast-title');
    const msgEl = toast.querySelector('.toast-message');

    if (titleEl) titleEl.textContent = title;
    if (msgEl) msgEl.textContent = message;

    // Update icon class
    if (iconEl) {
        iconEl.className = 'toast-icon ' + type;
        const iconMap = { success: 'fa-check', error: 'fa-times', warning: 'fa-exclamation' };
        const i = iconEl.querySelector('i');
        if (i) i.className = 'fas ' + (iconMap[type] || 'fa-check');
    }

    toast.classList.add('show');
    clearTimeout(window._toastTimeout);
    window._toastTimeout = setTimeout(() => toast.classList.remove('show'), 3000);
}

// ---- Reset Modal ----
function showResetConfirmation() {
    document.getElementById('resetModal').classList.add('show');
}

function closeResetConfirmation() {
    document.getElementById('resetModal').classList.remove('show');
}

async function confirmReset() {
    closeResetConfirmation();
    try {
        const result = await pywebview.api.reset_to_defaults();
        if (result && result.success) {
            showToast('Reset Complete', 'Advanced settings restored to defaults', 'success');
            await initializeUI();
        } else {
            showToast('Error', result ? result.message : 'Reset failed', 'error');
        }
    } catch (e) {
        showToast('Error', 'Failed to reset settings', 'error');
    }
}

// ---- Window Controls ----
function minimizeWindow() {
    pywebview.api.minimize_window();
}

function maximizeWindow() {
    pywebview.api.toggle_maximize();
}

function closeWindow() {
    pywebview.api.close_window();
}

// ---- Change Area (called from Python F2 hotkey) ----
async function changeArea() {
    try {
        await pywebview.api.change_area();
    } catch (e) { console.error(e); }
}

// ---- Window Drag ----
function setupWindowDrag() {
    const titleBar = document.getElementById('titleBar');
    if (!titleBar) return;

    let isDragging = false;
    let dragReady = false;
    let dragOffsetX = 0;
    let dragOffsetY = 0;
    let rafPending = false;
    let lastScreenX = 0;
    let lastScreenY = 0;

    titleBar.addEventListener('mousedown', async (e) => {
        if (e.target.closest('.window-controls') || e.target.closest('button')) return;

        isDragging = true;
        dragReady = false;
        document.body.style.userSelect = 'none';
        const startX = e.screenX;
        const startY = e.screenY;
        try {
            const pos = await pywebview.api.get_window_position();
            if (!isDragging) return;
            dragOffsetX = startX - pos.x;
            dragOffsetY = startY - pos.y;
            dragReady = true;
        } catch (err) {
            isDragging = false;
            dragReady = false;
            document.body.style.userSelect = '';
        }
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging || !dragReady) return;
        lastScreenX = e.screenX;
        lastScreenY = e.screenY;
        if (!rafPending) {
            rafPending = true;
            requestAnimationFrame(() => {
                rafPending = false;
                if (!isDragging || !dragReady) return;
                pywebview.api.set_window_position(lastScreenX - dragOffsetX, lastScreenY - dragOffsetY);
            });
        }
    });

    document.addEventListener('mouseup', () => {
        isDragging = false;
        dragReady = false;
        document.body.style.userSelect = '';
    });
}

// ---- Point Display Helper ----
function updatePointDisplay(elementId, point) {
    const el = document.getElementById(elementId);
    if (!el) return;
    if (point && point.x !== undefined && point.y !== undefined) {
        el.textContent = `X: ${point.x}, Y: ${point.y}`;
    } else {
        el.textContent = 'Not Set';
    }
}

// ---- Set Point Functions ----
async function setWaterPoint() {
    showToast('Set Point', 'Move mouse to water and LEFT CLICK', 'warning');
    try { await pywebview.api.set_water_point(); } catch (e) { console.error(e); }
}

async function setLeftPoint() {
    showToast('Set Point', 'Move mouse and LEFT CLICK', 'warning');
    try { await pywebview.api.set_left_point(); } catch (e) { console.error(e); }
}

async function setMiddlePoint() {
    showToast('Set Point', 'Move mouse and LEFT CLICK', 'warning');
    try { await pywebview.api.set_middle_point(); } catch (e) { console.error(e); }
}

async function setRightPoint() {
    showToast('Set Point', 'Move mouse and LEFT CLICK', 'warning');
    try { await pywebview.api.set_right_point(); } catch (e) { console.error(e); }
}

async function setBaitPoint() {
    showToast('Set Point', 'Move mouse and LEFT CLICK', 'warning');
    try { await pywebview.api.set_bait_point(); } catch (e) { console.error(e); }
}

async function setStoreFruitPoint() {
    showToast('Set Point', 'Move mouse and LEFT CLICK', 'warning');
    try { await pywebview.api.set_store_fruit_point(); } catch (e) { console.error(e); }
}

async function setCraftPoint1() {
    showToast('Set Point', 'Move mouse and LEFT CLICK', 'warning');
    try { await pywebview.api.set_craft_point_1(); } catch (e) { console.error(e); }
}

async function setCraftPoint2() {
    showToast('Set Point', 'Move mouse and LEFT CLICK', 'warning');
    try { await pywebview.api.set_craft_point_2(); } catch (e) { console.error(e); }
}

async function setCraftPoint3() {
    showToast('Set Point', 'Move mouse and LEFT CLICK', 'warning');
    try { await pywebview.api.set_craft_point_3(); } catch (e) { console.error(e); }
}

async function setCraftPoint4() {
    showToast('Set Point', 'Move mouse and LEFT CLICK', 'warning');
    try { await pywebview.api.set_craft_point_4(); } catch (e) { console.error(e); }
}

async function setLegBaitPoint() {
    showToast('Set Point', 'Move mouse and LEFT CLICK', 'warning');
    try { await pywebview.api.set_leg_bait_point(); } catch (e) { console.error(e); }
}

async function setRareBaitPoint() {
    showToast('Set Point', 'Move mouse and LEFT CLICK', 'warning');
    try { await pywebview.api.set_rare_bait_point(); } catch (e) { console.error(e); }
}

// ---- Toggle Functions ----
function setToggleState(elementId, active) {
    const el = document.getElementById(elementId);
    if (!el) return;
    if (active) {
        el.classList.add('active');
    } else {
        el.classList.remove('active');
    }
}

function setCheckboxState(elementId, checked) {
    const el = document.getElementById(elementId);
    if (!el) return;
    if (checked) {
        el.classList.add('checked');
    } else {
        el.classList.remove('checked');
    }
}

function isToggleActive(elementId) {
    const el = document.getElementById(elementId);
    return el ? el.classList.contains('active') : false;
}

function isCheckboxChecked(elementId) {
    const el = document.getElementById(elementId);
    return el ? el.classList.contains('checked') : false;
}

async function toggleAutoBuyBait() {
    const toggle = document.getElementById('autoBuyBaitToggle');
    if (!toggle) return;
    toggle.classList.toggle('active');
    const enabled = toggle.classList.contains('active');
    setSectionCollapse('autoBuySection', !enabled);
    try {
        await pywebview.api.toggle_auto_buy_bait(enabled);
    } catch (e) { console.error(e); }
}

async function toggleAutoCraftBait() {
    const toggle = document.getElementById('autoCraftBaitToggle');
    if (!toggle) return;
    toggle.classList.toggle('active');
    const enabled = toggle.classList.contains('active');
    setSectionCollapse('autoCraftSection', !enabled);
    try {
        await pywebview.api.toggle_auto_craft_bait(enabled);
    } catch (e) { console.error(e); }
}

async function toggleAutoSelectBait() {
    const toggle = document.getElementById('autoSelectBaitToggle');
    if (!toggle) return;
    toggle.classList.toggle('active');
    const enabled = toggle.classList.contains('active');
    setSectionCollapse('autoSelectSection', !enabled);
    try {
        await pywebview.api.toggle_auto_select_bait(enabled);
    } catch (e) { console.error(e); }
}

async function toggleAutoStoreFruit() {
    const toggle = document.getElementById('autoStoreFruitToggle');
    if (!toggle) return;
    toggle.classList.toggle('active');
    const enabled = toggle.classList.contains('active');
    setSectionCollapse('autoStoreSection', !enabled);
    try {
        await pywebview.api.toggle_auto_store_fruit(enabled);
    } catch (e) { console.error(e); }
}

async function toggleCraftLegBait() {
    const cb = document.getElementById('craftLegBaitCheckbox');
    if (!cb) return;
    cb.classList.toggle('checked');
    const enabled = cb.classList.contains('checked');
    try {
        await pywebview.api.toggle_craft_leg_bait(enabled);
    } catch (e) { console.error(e); }
    updateCraftBaitPointButtons();
}

async function toggleCraftRareBait() {
    const cb = document.getElementById('craftRareBaitCheckbox');
    if (!cb) return;
    cb.classList.toggle('checked');
    const enabled = cb.classList.contains('checked');
    try {
        await pywebview.api.toggle_craft_rare_bait(enabled);
    } catch (e) { console.error(e); }
    updateCraftBaitPointButtons();
}

function updateCraftBaitPointButtons() {
    const legEnabled = isCheckboxChecked('craftLegBaitCheckbox');
    const rareEnabled = isCheckboxChecked('craftRareBaitCheckbox');
    
    const legBtn = document.getElementById('legBaitSetPointBtn');
    const rareBtn = document.getElementById('rareBaitSetPointBtn');
    
    if (legBtn) legBtn.disabled = !legEnabled;
    if (rareBtn) rareBtn.disabled = !rareEnabled;
}

// ---- Keybind Updates ----
async function updateRodHotkey() {
    const select = document.getElementById('rodHotkeySelect');
    if (!select) return;
    try {
        await pywebview.api.update_rod_hotkey(select.value);
    } catch (e) { console.error(e); }
}

async function updateAnythingElseHotkey() {
    const select = document.getElementById('anythingElseHotkeySelect');
    if (!select) return;
    try {
        await pywebview.api.update_anything_else_hotkey(select.value);
    } catch (e) { console.error(e); }
}

async function updateDevilFruitHotkey() {
    const select = document.getElementById('devilFruitHotkeyDropdown');
    if (!select) return;
    try {
        await pywebview.api.update_devil_fruit_hotkey(select.value);
    } catch (e) { console.error(e); }
}

// ---- Advanced Parameter Updates ----
async function updatePDParams() {
    const kp = parseFloat(document.getElementById('kpInput').value);
    const kd = parseFloat(document.getElementById('kdInput').value);
    const pdClamp = parseFloat(document.getElementById('pdClampInput').value);
    try {
        await pywebview.api.update_pd_params(kp, kd, pdClamp);
    } catch (e) { console.error(e); }
}

async function updateCastTiming() {
    const castHold = parseFloat(document.getElementById('castHoldInput').value);
    const recastTimeout = parseFloat(document.getElementById('recastTimeoutInput').value);
    try {
        await pywebview.api.update_cast_timing(castHold, recastTimeout);
    } catch (e) { console.error(e); }
}

async function updateFishTiming() {
    const fishEndDelay = parseFloat(document.getElementById('fishEndDelayInput').value);
    try {
        await pywebview.api.update_fish_timing(fishEndDelay);
    } catch (e) { console.error(e); }
}

async function updateLoopsPerPurchase() {
    const loops = parseInt(document.getElementById('loopsPerPurchaseInput').value);
    try {
        await pywebview.api.update_loops_per_purchase(loops);
    } catch (e) { console.error(e); }
}

async function updateAdvancedTiming() {
    const params = {};
    
    // Auto Buy Bait Delays
    const preCastEDelay = document.getElementById('preCastEDelayInput');
    const preCastClickDelay = document.getElementById('preCastClickDelayInput');
    const preCastTypeDelay = document.getElementById('preCastTypeDelayInput');
    const preCastAntiDetectDelay = document.getElementById('preCastAntiDetectDelayInput');
    
    if (preCastEDelay) params.pre_cast_e_delay = parseFloat(preCastEDelay.value);
    if (preCastClickDelay) params.pre_cast_click_delay = parseFloat(preCastClickDelay.value);
    if (preCastTypeDelay) params.pre_cast_type_delay = parseFloat(preCastTypeDelay.value);
    if (preCastAntiDetectDelay) params.pre_cast_anti_detect_delay = parseFloat(preCastAntiDetectDelay.value);

    // Auto Select Bait Delay
    const autoSelectBaitDelay = document.getElementById('autoSelectBaitDelayInput');
    if (autoSelectBaitDelay) params.auto_select_bait_delay = parseFloat(autoSelectBaitDelay.value);

    // Store Devil Fruit Delays
    const storeFruitHotkeyDelay = document.getElementById('storeFruitHotkeyDelayInput');
    const storeFruitClickDelay = document.getElementById('storeFruitClickDelayInput');
    const storeFruitShiftDelay = document.getElementById('storeFruitShiftDelayInput');
    const storeFruitBackspaceDelay = document.getElementById('storeFruitBackspaceDelayInput');
    
    if (storeFruitHotkeyDelay) params.store_fruit_hotkey_delay = parseFloat(storeFruitHotkeyDelay.value);
    if (storeFruitClickDelay) params.store_fruit_click_delay = parseFloat(storeFruitClickDelay.value);
    if (storeFruitShiftDelay) params.store_fruit_shift_delay = parseFloat(storeFruitShiftDelay.value);
    if (storeFruitBackspaceDelay) params.store_fruit_backspace_delay = parseFloat(storeFruitBackspaceDelay.value);

    // Auto Craft Bait Other Timing
    const craftNavWaitDelay = document.getElementById('craftNavWaitDelayInput');
    const craftTPressDelay = document.getElementById('craftTPressDelayInput');
    const craftClickDelay = document.getElementById('craftClickDelayInput');
    const craftButtonDelay = document.getElementById('craftButtonDelayInput');
    const craftCraftButtonDelay = document.getElementById('craftCraftButtonDelayInput');
    const craftSequenceDelay = document.getElementById('craftSequenceDelayInput');
    const craftExitDelay = document.getElementById('craftExitDelayInput');
    
    if (craftNavWaitDelay) params.craft_nav_wait_delay = parseFloat(craftNavWaitDelay.value);
    if (craftTPressDelay) params.craft_t_press_delay = parseFloat(craftTPressDelay.value);
    if (craftClickDelay) params.craft_click_delay = parseFloat(craftClickDelay.value);
    if (craftButtonDelay) params.craft_button_delay = parseFloat(craftButtonDelay.value);
    if (craftCraftButtonDelay) params.craft_craft_button_delay = parseFloat(craftCraftButtonDelay.value);
    if (craftSequenceDelay) params.craft_sequence_delay = parseFloat(craftSequenceDelay.value);
    if (craftExitDelay) params.craft_exit_delay = parseFloat(craftExitDelay.value);

    // Navigation Path
    const craftNavKey1 = document.getElementById('craftNavKey1Input');
    const craftNavDuration1 = document.getElementById('craftNavDuration1Input');
    const craftNavKey2 = document.getElementById('craftNavKey2Input');
    const craftNavDuration2 = document.getElementById('craftNavDuration2Input');
    
    if (craftNavKey1) params.craft_nav_key_1 = craftNavKey1.value;
    if (craftNavDuration1) params.craft_nav_duration_1 = parseFloat(craftNavDuration1.value);
    if (craftNavKey2) params.craft_nav_key_2 = craftNavKey2.value;
    if (craftNavDuration2) params.craft_nav_duration_2 = parseFloat(craftNavDuration2.value);

    // Fishing Loop Delays
    const rodSelectDelay = document.getElementById('rodSelectDelayInput');
    const cursorAntiDetectDelay = document.getElementById('cursorAntiDetectDelayInput');
    const scanLoopDelay = document.getElementById('scanLoopDelayInput');
    
    if (rodSelectDelay) params.rod_select_delay = parseFloat(rodSelectDelay.value);
    if (cursorAntiDetectDelay) params.cursor_anti_detect_delay = parseFloat(cursorAntiDetectDelay.value);
    if (scanLoopDelay) params.scan_loop_delay = parseFloat(scanLoopDelay.value);

    // PD Control Advanced
    const pdApproachingDamping = document.getElementById('pdApproachingDampingInput');
    const pdChasingDamping = document.getElementById('pdChasingDampingInput');
    const gapToleranceMultiplier = document.getElementById('gapToleranceMultiplierInput');
    
    if (pdApproachingDamping) params.pd_approaching_damping = parseFloat(pdApproachingDamping.value);
    if (pdChasingDamping) params.pd_chasing_damping = parseFloat(pdChasingDamping.value);
    if (gapToleranceMultiplier) params.gap_tolerance_multiplier = parseFloat(gapToleranceMultiplier.value);

    try {
        await pywebview.api.update_advanced_timing(params);
    } catch (e) { console.error(e); }
}

// ---- Webhook Functions ----
async function saveWebhookSettings() {
    const url = document.getElementById('webhookUrlInput').value.trim();
    const userId = document.getElementById('discordUserIdInput').value.trim();
    try {
        const urlResult = await pywebview.api.update_webhook_url(url);
        if (urlResult && urlResult.status === 'error') {
            showToast('Error', urlResult.message, 'error');
            return;
        }
        await pywebview.api.update_discord_user_id(userId);
        showToast('Saved', 'Webhook settings saved successfully', 'success');
    } catch (e) {
        showToast('Error', 'Failed to save webhook settings', 'error');
    }
}

async function testWebhook() {
    showToast('Testing', 'Sending test webhook...', 'warning');
    try {
        const result = await pywebview.api.test_webhook();
        if (result && result.success) {
            showToast('Success', result.message, 'success');
        } else {
            showToast('Failed', result ? result.message : 'Test failed', 'error');
        }
    } catch (e) {
        showToast('Error', 'Failed to test webhook', 'error');
    }
}

async function toggleWebhookOption(option) {
    let elementId;
    if (option === 'devil_fruit') elementId = 'webhookDevilFruitToggle';
    else if (option === 'purchase') elementId = 'webhookPurchaseToggle';
    else if (option === 'recovery') elementId = 'webhookRecoveryToggle';
    
    const toggle = document.getElementById(elementId);
    if (!toggle) return;
    toggle.classList.toggle('active');
    const enabled = toggle.classList.contains('active');
    try {
        await pywebview.api.set_webhook_option(option, enabled);
    } catch (e) { console.error(e); }
}

// ---- Settings Functions ----
async function toggleWebhookPings() {
    const cb = document.getElementById('webhookPingsCheckbox');
    if (!cb) return;
    cb.classList.toggle('checked');
    const enabled = cb.classList.contains('checked');
    try {
        await pywebview.api.toggle_webhook_logging(enabled);
    } catch (e) { console.error(e); }
}

async function toggleStayOnTop() {
    const cb = document.getElementById('stayOnTopCheckbox');
    if (!cb) return;
    cb.classList.toggle('checked');
    const enabled = cb.classList.contains('checked');
    try {
        await pywebview.api.set_stay_on_top(enabled);
        showToast('Settings', 'Stay on top will apply on next restart', 'success');
    } catch (e) { console.error(e); }
}

async function toggleMinimizeOnRun() {
    const cb = document.getElementById('minimizeCheckbox');
    if (!cb) return;
    cb.classList.toggle('checked');
    const enabled = cb.classList.contains('checked');
    try {
        await pywebview.api.set_minimize_on_run(enabled);
    } catch (e) { console.error(e); }
}

// ---- Initialize UI from saved state ----
async function initializeUI() {
    try {
        const state = await pywebview.api.get_state();
        if (!state) return;

        // Keybinds
        const rodSelect = document.getElementById('rodHotkeySelect');
        if (rodSelect) rodSelect.value = state.rod_hotkey || '1';
        
        const anythingSelect = document.getElementById('anythingElseHotkeySelect');
        if (anythingSelect) anythingSelect.value = state.anything_else_hotkey || '2';
        
        const fruitSelect = document.getElementById('devilFruitHotkeyDropdown');
        if (fruitSelect) fruitSelect.value = state.devil_fruit_hotkey || '3';

        // Points 
        updatePointDisplay('waterPointDisplay', state.water_point);
        updatePointDisplay('leftPointDisplay', state.left_point);
        updatePointDisplay('middlePointDisplay', state.middle_point);
        updatePointDisplay('rightPointDisplay', state.right_point);
        updatePointDisplay('baitPointDisplay', state.bait_point);
        updatePointDisplay('storeFruitPointDisplay', state.store_fruit_point);
        updatePointDisplay('craftPoint1Display', state.craft_point_1);
        updatePointDisplay('craftPoint2Display', state.craft_point_2);
        updatePointDisplay('craftPoint3Display', state.craft_point_3);
        updatePointDisplay('craftPoint4Display', state.craft_point_4);
        updatePointDisplay('legBaitPointDisplay', state.leg_bait_point);
        updatePointDisplay('rareBaitPointDisplay', state.rare_bait_point);

        // Feature Toggles (div-based)
        setToggleState('autoBuyBaitToggle', state.auto_buy_common_bait);
        setToggleState('autoCraftBaitToggle', state.auto_craft_bait);
        setToggleState('autoSelectBaitToggle', state.auto_select_top_bait);
        setToggleState('autoStoreFruitToggle', state.auto_store_devil_fruit);

        // Craft bait checkboxes
        setCheckboxState('craftLegBaitCheckbox', state.craft_leg_bait);
        setCheckboxState('craftRareBaitCheckbox', state.craft_rare_bait);
        updateCraftBaitPointButtons();

        // Loops per purchase
        const loopsInput = document.getElementById('loopsPerPurchaseInput');
        if (loopsInput) loopsInput.value = state.loops_per_purchase || 100;

        // Webhook
        const webhookUrl = document.getElementById('webhookUrlInput');
        if (webhookUrl) webhookUrl.value = state.webhook_url || '';
        
        const discordUserId = document.getElementById('discordUserIdInput');
        if (discordUserId) discordUserId.value = state.discord_user_id || '';

        // Webhook notification toggles
        setToggleState('webhookDevilFruitToggle', state.webhook_notify_devil_fruit !== false);
        setToggleState('webhookPurchaseToggle', state.webhook_notify_purchase !== false);
        setToggleState('webhookRecoveryToggle', state.webhook_notify_recovery !== false);

        // Settings checkboxes
        setCheckboxState('webhookPingsCheckbox', state.webhook_enabled);
        setCheckboxState('stayOnTopCheckbox', state.stay_on_top !== false);
        setCheckboxState('minimizeCheckbox', state.minimize_on_run);

        // Advanced - PD Controller
        setInputValue('kpInput', state.kp);
        setInputValue('kdInput', state.kd);
        setInputValue('pdClampInput', state.pd_clamp);

        // Advanced - Auto Buy Bait Delays
        setInputValue('preCastEDelayInput', state.pre_cast_e_delay);
        setInputValue('preCastClickDelayInput', state.pre_cast_click_delay);
        setInputValue('preCastTypeDelayInput', state.pre_cast_type_delay);
        setInputValue('preCastAntiDetectDelayInput', state.pre_cast_anti_detect_delay);

        // Advanced - Auto Select Bait Delay
        setInputValue('autoSelectBaitDelayInput', state.auto_select_bait_delay);

        // Advanced - Store Devil Fruit Delays
        setInputValue('storeFruitHotkeyDelayInput', state.store_fruit_hotkey_delay);
        setInputValue('storeFruitClickDelayInput', state.store_fruit_click_delay);
        setInputValue('storeFruitShiftDelayInput', state.store_fruit_shift_delay);
        setInputValue('storeFruitBackspaceDelayInput', state.store_fruit_backspace_delay);

        // Advanced - Craft Bait Other Timing
        setInputValue('craftNavWaitDelayInput', state.craft_nav_wait_delay);
        setInputValue('craftTPressDelayInput', state.craft_t_press_delay);
        setInputValue('craftClickDelayInput', state.craft_click_delay);
        setInputValue('craftButtonDelayInput', state.craft_button_delay);
        setInputValue('craftCraftButtonDelayInput', state.craft_craft_button_delay);
        setInputValue('craftSequenceDelayInput', state.craft_sequence_delay);
        setInputValue('craftExitDelayInput', state.craft_exit_delay);

        // Advanced - Fishing Loop Delays
        setInputValue('castHoldInput', state.cast_hold_duration);
        setInputValue('recastTimeoutInput', state.recast_timeout);
        setInputValue('fishEndDelayInput', state.fish_end_delay);
        setInputValue('rodSelectDelayInput', state.rod_select_delay);
        setInputValue('cursorAntiDetectDelayInput', state.cursor_anti_detect_delay);
        setInputValue('scanLoopDelayInput', state.scan_loop_delay);

        // Advanced - PD Control Advanced
        setInputValue('pdApproachingDampingInput', state.pd_approaching_damping);
        setInputValue('pdChasingDampingInput', state.pd_chasing_damping);
        setInputValue('gapToleranceMultiplierInput', state.gap_tolerance_multiplier);

        // Navigation Path
        setInputValue('craftNavKey1Input', state.craft_nav_key_1);
        setInputValue('craftNavDuration1Input', state.craft_nav_duration_1);
        setInputValue('craftNavKey2Input', state.craft_nav_key_2);
        setInputValue('craftNavDuration2Input', state.craft_nav_duration_2);

    } catch (e) {
        console.error('Failed to initialize UI:', e);
    }
}

function setInputValue(id, value) {
    const el = document.getElementById(id);
    if (el && value !== undefined && value !== null) {
        el.value = value;
    }
}

// ---- Periodic State Update ----
async function updateUI() {
    try {
        const state = await pywebview.api.get_state();
        if (!state) return;

        // Update point displays (they can change from background click-to-set)
        updatePointDisplay('waterPointDisplay', state.water_point);
        updatePointDisplay('leftPointDisplay', state.left_point);
        updatePointDisplay('middlePointDisplay', state.middle_point);
        updatePointDisplay('rightPointDisplay', state.right_point);
        updatePointDisplay('baitPointDisplay', state.bait_point);
        updatePointDisplay('storeFruitPointDisplay', state.store_fruit_point);
        updatePointDisplay('craftPoint1Display', state.craft_point_1);
        updatePointDisplay('craftPoint2Display', state.craft_point_2);
        updatePointDisplay('craftPoint3Display', state.craft_point_3);
        updatePointDisplay('craftPoint4Display', state.craft_point_4);
        updatePointDisplay('legBaitPointDisplay', state.leg_bait_point);
        updatePointDisplay('rareBaitPointDisplay', state.rare_bait_point);

        // Sync toggle states from backend (handles F1 hotkey external changes)
        setToggleState('autoBuyBaitToggle', state.auto_buy_common_bait);
        setToggleState('autoCraftBaitToggle', state.auto_craft_bait);
        setToggleState('autoSelectBaitToggle', state.auto_select_top_bait);
        setToggleState('autoStoreFruitToggle', state.auto_store_devil_fruit);
        setCheckboxState('craftLegBaitCheckbox', state.craft_leg_bait);
        setCheckboxState('craftRareBaitCheckbox', state.craft_rare_bait);
        updateCraftBaitPointButtons();

        // Update status dot based on running state
        const statusDot = document.querySelector('.status-dot');
        if (statusDot) {
            statusDot.style.background = state.running ? 'var(--success)' : 'var(--text-muted)';
        }
    } catch (e) {
        // Silently fail - API might not be ready
    }
}

// ---- Loading Status ----
function updateLoadingStatus(msg) {
    const el = document.getElementById('loadingStatus');
    if (el) el.textContent = msg;
}

// ---- Backend Ready Handler ----
function onBackendReady(success, errorsStr) {
    // Show error toasts if any init issues
    if (!success && errorsStr && errorsStr !== '[]') {
        try {
            // Parse the errors string back
            const cleaned = errorsStr.replace(/^\[|\]$/g, '').replace(/^'|'$/g, '');
            if (cleaned) {
                showToast('Warning', cleaned, 'warning');
            }
        } catch (e) {
            showToast('Warning', 'Some features may not be available', 'warning');
        }
    }

    // Fade out loading screen, fade in app
    const loader = document.getElementById('loadingScreen');
    const app = document.getElementById('appContainer');
    if (app) app.style.transition = 'opacity 0.4s ease';
    if (app) app.style.opacity = '1';
    if (loader) loader.classList.add('hidden');
}

// ---- Startup ----
window.addEventListener('pywebviewready', async () => {
    updateLoadingStatus('Connecting to backend...');
    await initializeUI();
    setupWindowDrag();
    setInterval(updateUI, 1000);
});

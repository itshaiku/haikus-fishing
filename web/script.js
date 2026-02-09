

let updateInterval = null;

window.addEventListener('pywebviewready', function() {
    console.log('PyWebView is ready!');
    initializeUI();
    startStateUpdates();
    setupWindowDrag();
});

if (typeof pywebview === 'undefined') {
    console.log('Preview mode - pywebview not available');
    window.addEventListener('DOMContentLoaded', function() {
        console.log('DOM loaded in preview mode');
    });
}

async function initializeUI() {
    try {
        console.log('Initializing UI with saved coordinates...');
        const state = await pywebview.api.get_state();

        updatePointDisplay('waterPointDisplay', state.water_point);
        updatePointDisplay('areaBoxDisplay', state.area_box, true);
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

        if (document.getElementById('autoBuyBaitToggle')) {
            document.getElementById('autoBuyBaitToggle').checked = state.auto_buy_common_bait;
        }
        if (document.getElementById('autoSelectBaitToggle')) {
            document.getElementById('autoSelectBaitToggle').checked = state.auto_select_top_bait;
        }
        if (document.getElementById('autoStoreFruitToggle')) {
            document.getElementById('autoStoreFruitToggle').checked = state.auto_store_devil_fruit || false;
        }
        if (document.getElementById('autoCraftBaitToggle')) {
            document.getElementById('autoCraftBaitToggle').checked = state.auto_craft_bait || false;
        }

        if (document.getElementById('autoBuySection')) {
            const section = document.getElementById('autoBuySection');
            if (state.auto_buy_common_bait) {
                section.style.display = 'block';
                section.classList.add('expanded');
            } else {
                section.style.display = 'none';
            }
        }
        if (document.getElementById('autoSelectSection')) {
            const section = document.getElementById('autoSelectSection');
            if (state.auto_select_top_bait) {
                section.style.display = 'block';
                section.classList.add('expanded');
            } else {
                section.style.display = 'none';
            }
        }
        if (document.getElementById('autoStoreSection')) {
            const section = document.getElementById('autoStoreSection');
            if (state.auto_store_devil_fruit) {
                section.style.display = 'block';
                section.classList.add('expanded');
            } else {
                section.style.display = 'none';
            }
        }
        if (document.getElementById('autoCraftSection')) {
            const section = document.getElementById('autoCraftSection');
            if (state.auto_craft_bait) {
                section.style.display = 'block';
                section.classList.add('expanded');
            } else {
                section.style.display = 'none';
            }
        }

        if (document.getElementById('devilFruitHotkeyDropdown') && state.devil_fruit_hotkey) {
            document.getElementById('devilFruitHotkeyDropdown').value = state.devil_fruit_hotkey;
        }
        if (document.getElementById('webhookUrlInput') && state.webhook_url) {
            document.getElementById('webhookUrlInput').value = state.webhook_url;
        }

        if (document.getElementById('discordUserIdInput') && state.discord_user_id) {
            document.getElementById('discordUserIdInput').value = state.discord_user_id;
        }

        if (document.getElementById('webhookDevilFruitToggle')) {
            document.getElementById('webhookDevilFruitToggle').checked = state.webhook_notify_devil_fruit !== false;
        }
        if (document.getElementById('webhookPurchaseToggle')) {
            document.getElementById('webhookPurchaseToggle').checked = state.webhook_notify_purchase !== false;
        }
        if (document.getElementById('webhookRecoveryToggle')) {
            document.getElementById('webhookRecoveryToggle').checked = state.webhook_notify_recovery !== false;
        }
        if (document.getElementById('minimizeToggle')) {
            document.getElementById('minimizeToggle').checked = state.minimize_on_run || false;
        }

        if (document.getElementById('castHoldInput') && state.cast_hold_duration !== undefined) {
            document.getElementById('castHoldInput').value = state.cast_hold_duration;
        }
        if (document.getElementById('recastTimeoutInput') && state.recast_timeout !== undefined) {
            document.getElementById('recastTimeoutInput').value = state.recast_timeout;
        }
        if (document.getElementById('fishEndDelayInput') && state.fish_end_delay !== undefined) {
            document.getElementById('fishEndDelayInput').value = state.fish_end_delay;
        }

        if (document.getElementById('kpInput') && state.kp !== undefined) {
            document.getElementById('kpInput').value = state.kp;
        }
        if (document.getElementById('kdInput') && state.kd !== undefined) {
            document.getElementById('kdInput').value = state.kd;
        }
        if (document.getElementById('pdClampInput') && state.pd_clamp !== undefined) {
            document.getElementById('pdClampInput').value = state.pd_clamp;
        }

        if (document.getElementById('loopsPerPurchaseInput') && state.loops_per_purchase !== undefined) {
            document.getElementById('loopsPerPurchaseInput').value = state.loops_per_purchase;
        }

        if (document.getElementById('craftLegBaitToggle')) {
            document.getElementById('craftLegBaitToggle').checked = state.craft_leg_bait || false;
            if (document.getElementById('legBaitSetPointBtn')) {
                document.getElementById('legBaitSetPointBtn').disabled = !(state.craft_leg_bait || false);
            }
        }
        if (document.getElementById('craftRareBaitToggle')) {
            document.getElementById('craftRareBaitToggle').checked = state.craft_rare_bait || false;
            if (document.getElementById('rareBaitSetPointBtn')) {
                document.getElementById('rareBaitSetPointBtn').disabled = !(state.craft_rare_bait || false);
            }
        }

        if (document.getElementById('preCastEDelayInput') && state.pre_cast_e_delay !== undefined) {
            document.getElementById('preCastEDelayInput').value = state.pre_cast_e_delay;
        }
        if (document.getElementById('preCastClickDelayInput') && state.pre_cast_click_delay !== undefined) {
            document.getElementById('preCastClickDelayInput').value = state.pre_cast_click_delay;
        }
        if (document.getElementById('preCastTypeDelayInput') && state.pre_cast_type_delay !== undefined) {
            document.getElementById('preCastTypeDelayInput').value = state.pre_cast_type_delay;
        }
        if (document.getElementById('preCastAntiDetectDelayInput') && state.pre_cast_anti_detect_delay !== undefined) {
            document.getElementById('preCastAntiDetectDelayInput').value = state.pre_cast_anti_detect_delay;
        }
        if (document.getElementById('autoSelectBaitDelayInput') && state.auto_select_bait_delay !== undefined) {
            document.getElementById('autoSelectBaitDelayInput').value = state.auto_select_bait_delay;
        }
        if (document.getElementById('storeFruitHotkeyDelayInput') && state.store_fruit_hotkey_delay !== undefined) {
            document.getElementById('storeFruitHotkeyDelayInput').value = state.store_fruit_hotkey_delay;
        }
        if (document.getElementById('storeFruitClickDelayInput') && state.store_fruit_click_delay !== undefined) {
            document.getElementById('storeFruitClickDelayInput').value = state.store_fruit_click_delay;
        }
        if (document.getElementById('storeFruitShiftDelayInput') && state.store_fruit_shift_delay !== undefined) {
            document.getElementById('storeFruitShiftDelayInput').value = state.store_fruit_shift_delay;
        }
        if (document.getElementById('storeFruitBackspaceDelayInput') && state.store_fruit_backspace_delay !== undefined) {
            document.getElementById('storeFruitBackspaceDelayInput').value = state.store_fruit_backspace_delay;
        }
        if (document.getElementById('craftNavKey1Input') && state.craft_nav_key_1 !== undefined) {
            document.getElementById('craftNavKey1Input').value = state.craft_nav_key_1;
        }
        if (document.getElementById('craftNavDuration1Input') && state.craft_nav_duration_1 !== undefined) {
            document.getElementById('craftNavDuration1Input').value = state.craft_nav_duration_1;
        }
        if (document.getElementById('craftNavKey2Input') && state.craft_nav_key_2 !== undefined) {
            document.getElementById('craftNavKey2Input').value = state.craft_nav_key_2;
        }
        if (document.getElementById('craftNavDuration2Input') && state.craft_nav_duration_2 !== undefined) {
            document.getElementById('craftNavDuration2Input').value = state.craft_nav_duration_2;
        }
        if (document.getElementById('craftNavKey3Input') && state.craft_nav_key_3 !== undefined) {
            document.getElementById('craftNavKey3Input').value = state.craft_nav_key_3;
        }
        if (document.getElementById('craftNavDuration3Input') && state.craft_nav_duration_3 !== undefined) {
            document.getElementById('craftNavDuration3Input').value = state.craft_nav_duration_3;
        }
        if (document.getElementById('craftNavKey4Input') && state.craft_nav_key_4 !== undefined) {
            document.getElementById('craftNavKey4Input').value = state.craft_nav_key_4;
        }
        if (document.getElementById('craftNavDuration4Input') && state.craft_nav_duration_4 !== undefined) {
            document.getElementById('craftNavDuration4Input').value = state.craft_nav_duration_4;
        }
        if (document.getElementById('craftNavWaitDelayInput') && state.craft_nav_wait_delay !== undefined) {
            document.getElementById('craftNavWaitDelayInput').value = state.craft_nav_wait_delay;
        }
        if (document.getElementById('craftTPressDelayInput') && state.craft_t_press_delay !== undefined) {
            document.getElementById('craftTPressDelayInput').value = state.craft_t_press_delay;
        }
        if (document.getElementById('craftClickDelayInput') && state.craft_click_delay !== undefined) {
            document.getElementById('craftClickDelayInput').value = state.craft_click_delay;
        }
        if (document.getElementById('craftButtonDelayInput') && state.craft_button_delay !== undefined) {
            document.getElementById('craftButtonDelayInput').value = state.craft_button_delay;
        }
        if (document.getElementById('craftCraftButtonDelayInput') && state.craft_craft_button_delay !== undefined) {
            document.getElementById('craftCraftButtonDelayInput').value = state.craft_craft_button_delay;
        }
        if (document.getElementById('craftSequenceDelayInput') && state.craft_sequence_delay !== undefined) {
            document.getElementById('craftSequenceDelayInput').value = state.craft_sequence_delay;
        }
        if (document.getElementById('craftExitDelayInput') && state.craft_exit_delay !== undefined) {
            document.getElementById('craftExitDelayInput').value = state.craft_exit_delay;
        }
        if (document.getElementById('rodSelectDelayInput') && state.rod_select_delay !== undefined) {
            document.getElementById('rodSelectDelayInput').value = state.rod_select_delay;
        }
        if (document.getElementById('cursorAntiDetectDelayInput') && state.cursor_anti_detect_delay !== undefined) {
            document.getElementById('cursorAntiDetectDelayInput').value = state.cursor_anti_detect_delay;
        }
        if (document.getElementById('scanLoopDelayInput') && state.scan_loop_delay !== undefined) {
            document.getElementById('scanLoopDelayInput').value = state.scan_loop_delay;
        }
        if (document.getElementById('pdApproachingDampingInput') && state.pd_approaching_damping !== undefined) {
            document.getElementById('pdApproachingDampingInput').value = state.pd_approaching_damping;
        }
        if (document.getElementById('pdChasingDampingInput') && state.pd_chasing_damping !== undefined) {
            document.getElementById('pdChasingDampingInput').value = state.pd_chasing_damping;
        }
        if (document.getElementById('gapToleranceMultiplierInput') && state.gap_tolerance_multiplier !== undefined) {
            document.getElementById('gapToleranceMultiplierInput').value = state.gap_tolerance_multiplier;
        }
        
        console.log('UI initialized successfully!');
    } catch (error) {
        console.error('Error initializing UI:', error);
    }
}

function setupWindowDrag() {
    const titleBar = document.getElementById('titleBar');
    if (!titleBar) return;
    
    let initialX, initialY, windowX, windowY;
    let animationFrameId = null;
    let targetX, targetY;
    
    titleBar.addEventListener('mousedown', function(e) {
        if (e.target.closest('.window-btn')) {
            return;
        }
        
        initialX = e.screenX;
        initialY = e.screenY;
        
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.get_window_position().then(function(pos) {
                windowX = pos.x;
                windowY = pos.y;
                
                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });
        }
    });
    
    function onMouseMove(e) {
        targetX = windowX + (e.screenX - initialX);
        targetY = windowY + (e.screenY - initialY);
        
        if (!animationFrameId) {
            animationFrameId = requestAnimationFrame(updateWindowPosition);
        }
    }
    
    function updateWindowPosition() {
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.set_window_position(targetX, targetY);
        }
        animationFrameId = null;
    }
    
    function onMouseUp() {
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
        if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
            animationFrameId = null;
        }
    }
}

function startStateUpdates() {
    updateUI();
    updateInterval = setInterval(updateUI, 1000);
}

async function updateUI() {
    console.log('=== updateUI called ===');
    try {
        console.log('About to call get_state()...');
        const state = await pywebview.api.get_state();
        console.log('✓ Got state:', JSON.stringify(state, null, 2));



        console.log('=== Updating point displays ===');
        console.log('left_point:', state.left_point);
        updatePointDisplay('waterPointDisplay', state.water_point);
        updatePointDisplay('areaBoxDisplay', state.area_box, true);
        updatePointDisplay('leftPointDisplay', state.left_point);
        updatePointDisplay('middlePointDisplay', state.middle_point);
        updatePointDisplay('rightPointDisplay', state.right_point);
        updatePointDisplay('baitPointDisplay', state.bait_point);
        updatePointDisplay('storeFruitPointDisplay', state.store_fruit_point);
        updatePointDisplay('craftPoint1Display', state.craft_point_1);
        updatePointDisplay('craftPoint2Display', state.craft_point_2);
        updatePointDisplay('craftPoint3Display', state.craft_point_3);
        updatePointDisplay('craftPoint4Display', state.craft_point_4);
        console.log('=== Point displays updated ===');

        if (document.getElementById('autoBuyBaitToggle')) {
            document.getElementById('autoBuyBaitToggle').checked = state.auto_buy_common_bait;
        }
        if (document.getElementById('autoSelectBaitToggle')) {
            document.getElementById('autoSelectBaitToggle').checked = state.auto_select_top_bait;
        }
        if (document.getElementById('autoCraftBaitToggle')) {
            document.getElementById('autoCraftBaitToggle').checked = state.auto_craft_bait || false;
        }

        if (document.getElementById('autoBuySection')) {
            document.getElementById('autoBuySection').style.display = state.auto_buy_common_bait ? 'block' : 'none';
        }
        if (document.getElementById('autoSelectSection')) {
            document.getElementById('autoSelectSection').style.display = state.auto_select_top_bait ? 'block' : 'none';
        }
        if (document.getElementById('autoCraftSection')) {
            document.getElementById('autoCraftSection').style.display = state.auto_craft_bait ? 'block' : 'none';
        }


        console.log('=== updateUI completed ===');
    } catch (error) {
        console.error('❌ ERROR in updateUI:', error);
        console.error('Error stack:', error.stack);
    }
}

function updatePointDisplay(elementId, point, isBox = false) {
    const element = document.getElementById(elementId);
    if (!element) {
        console.error('Element not found:', elementId);
        return;
    }
    
    console.log(`[${elementId}] Received point:`, JSON.stringify(point));

    let hasValidCoords = false;
    if (point && typeof point === 'object') {
        if (isBox) {
            hasValidCoords = typeof point.x1 === 'number' && typeof point.y1 === 'number' && 
                            typeof point.x2 === 'number' && typeof point.y2 === 'number';
            console.log(`[${elementId}] Box validation - x1:${point.x1} y1:${point.y1} x2:${point.x2} y2:${point.y2} valid:${hasValidCoords}`);
        } else {
            hasValidCoords = typeof point.x === 'number' && typeof point.y === 'number';
            console.log(`[${elementId}] Point validation - x:${point.x} (${typeof point.x}) y:${point.y} (${typeof point.y}) valid:${hasValidCoords}`);
        }
    } else {
        console.log(`[${elementId}] Point is null/undefined or not an object`);
    }
    
    if (hasValidCoords) {
        if (isBox) {
            element.textContent = `X1: ${point.x1}, Y1: ${point.y1}, X2: ${point.x2}, Y2: ${point.y2}`;
        } else {
            element.textContent = `X: ${point.x}, Y: ${point.y}`;
        }
        element.style.color = '';
        console.log(`[${elementId}] ✓ Display set to: "${element.textContent}"`);
    } else {
        element.textContent = '';
        element.style.color = '';
        console.log(`[${elementId}] ✗ Display cleared (will show "Not Set")`);
    }
}

async function setWaterPoint() {
    try {
        const initialState = await pywebview.api.get_state();
        const oldPoint = JSON.stringify(initialState.water_point);
        await pywebview.api.set_water_point();
        
        let attempts = 0;
        const pollInterval = setInterval(async () => {
            const state = await pywebview.api.get_state();
            const newPoint = JSON.stringify(state.water_point);
            if (newPoint !== oldPoint || attempts++ > 150) {
                clearInterval(pollInterval);
                updatePointDisplay('waterPointDisplay', state.water_point);
            }
        }, 200);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function setLeftPoint() {
    try {
        console.log('Setting left point...');
        const initialState = await pywebview.api.get_state();
        const oldPoint = JSON.stringify(initialState.left_point);
        await pywebview.api.set_left_point();
        console.log('Waiting for coordinate update...');

        let attempts = 0;
        const pollInterval = setInterval(async () => {
            const state = await pywebview.api.get_state();
            const newPoint = JSON.stringify(state.left_point);
            if (newPoint !== oldPoint || attempts++ > 150) {
                clearInterval(pollInterval);
                updatePointDisplay('leftPointDisplay', state.left_point);
                console.log('Left point updated!');
            }
        }, 200);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function setMiddlePoint() {
    try {
        const initialState = await pywebview.api.get_state();
        const oldPoint = JSON.stringify(initialState.middle_point);
        await pywebview.api.set_middle_point();
        
        let attempts = 0;
        const pollInterval = setInterval(async () => {
            const state = await pywebview.api.get_state();
            const newPoint = JSON.stringify(state.middle_point);
            if (newPoint !== oldPoint || attempts++ > 150) {
                clearInterval(pollInterval);
                updatePointDisplay('middlePointDisplay', state.middle_point);
            }
        }, 200);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function setRightPoint() {
    try {
        const initialState = await pywebview.api.get_state();
        const oldPoint = JSON.stringify(initialState.right_point);
        await pywebview.api.set_right_point();
        
        let attempts = 0;
        const pollInterval = setInterval(async () => {
            const state = await pywebview.api.get_state();
            const newPoint = JSON.stringify(state.right_point);
            if (newPoint !== oldPoint || attempts++ > 150) {
                clearInterval(pollInterval);
                updatePointDisplay('rightPointDisplay', state.right_point);
            }
        }, 200);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function setBaitPoint() {
    try {
        const initialState = await pywebview.api.get_state();
        const oldPoint = JSON.stringify(initialState.bait_point);
        await pywebview.api.set_bait_point();
        
        let attempts = 0;
        const pollInterval = setInterval(async () => {
            const state = await pywebview.api.get_state();
            const newPoint = JSON.stringify(state.bait_point);
            if (newPoint !== oldPoint || attempts++ > 150) {
                clearInterval(pollInterval);
                updatePointDisplay('baitPointDisplay', state.bait_point);
            }
        }, 200);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function setStoreFruitPoint() {
    try {
        const initialState = await pywebview.api.get_state();
        const oldPoint = JSON.stringify(initialState.store_fruit_point);
        await pywebview.api.set_store_fruit_point();
        
        let attempts = 0;
        const pollInterval = setInterval(async () => {
            const state = await pywebview.api.get_state();
            const newPoint = JSON.stringify(state.store_fruit_point);
            if (newPoint !== oldPoint || attempts++ > 150) {
                clearInterval(pollInterval);
                updatePointDisplay('storeFruitPointDisplay', state.store_fruit_point);
            }
        }, 200);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function setCraftPoint1() {
    try {
        const initialState = await pywebview.api.get_state();
        const oldPoint = JSON.stringify(initialState.craft_point_1);
        await pywebview.api.set_craft_point_1();
        
        let attempts = 0;
        const pollInterval = setInterval(async () => {
            const state = await pywebview.api.get_state();
            const newPoint = JSON.stringify(state.craft_point_1);
            if (newPoint !== oldPoint || attempts++ > 150) {
                clearInterval(pollInterval);
                updatePointDisplay('craftPoint1Display', state.craft_point_1);
            }
        }, 200);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function setCraftPoint2() {
    try {
        const initialState = await pywebview.api.get_state();
        const oldPoint = JSON.stringify(initialState.craft_point_2);
        await pywebview.api.set_craft_point_2();
        
        let attempts = 0;
        const pollInterval = setInterval(async () => {
            const state = await pywebview.api.get_state();
            const newPoint = JSON.stringify(state.craft_point_2);
            if (newPoint !== oldPoint || attempts++ > 150) {
                clearInterval(pollInterval);
                updatePointDisplay('craftPoint2Display', state.craft_point_2);
            }
        }, 200);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function setCraftPoint3() {
    try {
        const initialState = await pywebview.api.get_state();
        const oldPoint = JSON.stringify(initialState.craft_point_3);
        await pywebview.api.set_craft_point_3();
        
        let attempts = 0;
        const pollInterval = setInterval(async () => {
            const state = await pywebview.api.get_state();
            const newPoint = JSON.stringify(state.craft_point_3);
            if (newPoint !== oldPoint || attempts++ > 150) {
                clearInterval(pollInterval);
                updatePointDisplay('craftPoint3Display', state.craft_point_3);
            }
        }, 200);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function setCraftPoint4() {
    try {
        const initialState = await pywebview.api.get_state();
        const oldPoint = JSON.stringify(initialState.craft_point_4);
        await pywebview.api.set_craft_point_4();
        
        let attempts = 0;
        const pollInterval = setInterval(async () => {
            const state = await pywebview.api.get_state();
            const newPoint = JSON.stringify(state.craft_point_4);
            if (newPoint !== oldPoint || attempts++ > 150) {
                clearInterval(pollInterval);
                updatePointDisplay('craftPoint4Display', state.craft_point_4);
            }
        }, 200);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function changeArea() {
    try {
        const result = await pywebview.api.change_area();
        if (result.status === 'showing') {

            const checkInterval = setInterval(async () => {
                updateUI();
            }, 500);
            setTimeout(() => {
                clearInterval(checkInterval);
            }, 30000);
        }
    } catch (error) {
        console.error('Error: ' + error);
    }
}




async function updatePDParams() {
    try {
        const kp = parseFloat(document.getElementById('kpInput').value);
        const kd = parseFloat(document.getElementById('kdInput').value);
        const pdClamp = parseFloat(document.getElementById('pdClampInput').value);
        
        await pywebview.api.update_pd_params(kp, kd, pdClamp);
    } catch (error) {
        console.error('Error updating PD params: ' + error);
    }
}

async function updateCastTiming() {
    try {
        const castHold = parseFloat(document.getElementById('castHoldInput').value);
        const recastTimeout = parseFloat(document.getElementById('recastTimeoutInput').value);
        
        await pywebview.api.update_cast_timing(castHold, recastTimeout);
    } catch (error) {
        console.error('Error updating cast timing: ' + error);
    }
}

async function updateFishTiming() {
    try {
        const fishEndDelay = parseFloat(document.getElementById('fishEndDelayInput').value);
        
        await pywebview.api.update_fish_timing(fishEndDelay);
    } catch (error) {
        console.error('Error updating fish timing: ' + error);
    }
}

async function updateRodHotkey() {
    try {
        const hotkey = document.getElementById('rodHotkeySelect').value;
        await pywebview.api.update_rod_hotkey(hotkey);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function updateAnythingElseHotkey() {
    try {
        const hotkey = document.getElementById('anythingElseHotkeySelect').value;
        await pywebview.api.update_anything_else_hotkey(hotkey);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function toggleAutoBuyBait() {
    try {
        const enabled = document.getElementById('autoBuyBaitToggle').checked;
        if (typeof pywebview !== 'undefined') {
            await pywebview.api.toggle_auto_buy_bait(enabled);
        }
        const section = document.getElementById('autoBuySection');
        if (enabled) {
            section.style.display = 'block';
            section.offsetHeight;
            section.classList.add('expanded');
        } else {
            section.classList.remove('expanded');
            setTimeout(() => section.style.display = 'none', 300);
        }
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function toggleAutoSelectBait() {
    try {
        const enabled = document.getElementById('autoSelectBaitToggle').checked;
        if (typeof pywebview !== 'undefined') {
            await pywebview.api.toggle_auto_select_bait(enabled);
        }
        const section = document.getElementById('autoSelectSection');
        if (enabled) {
            section.style.display = 'block';
            section.offsetHeight;
            section.classList.add('expanded');
        } else {
            section.classList.remove('expanded');
            setTimeout(() => section.style.display = 'none', 300);
        }
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function toggleAutoStoreFruit() {
    try {
        const enabled = document.getElementById('autoStoreFruitToggle').checked;
        if (typeof pywebview !== 'undefined') {
            await pywebview.api.toggle_auto_store_fruit(enabled);
        }
        const section = document.getElementById('autoStoreSection');
        if (enabled) {
            section.style.display = 'block';
            section.offsetHeight;
            section.classList.add('expanded');
        } else {
            section.classList.remove('expanded');
            setTimeout(() => section.style.display = 'none', 300);
        }
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function toggleAutoCraftBait() {
    try {
        const enabled = document.getElementById('autoCraftBaitToggle').checked;
        if (typeof pywebview !== 'undefined') {
            await pywebview.api.toggle_auto_craft_bait(enabled);
        }
        const section = document.getElementById('autoCraftSection');
        if (enabled) {
            section.style.display = 'block';
            section.offsetHeight;
            section.classList.add('expanded');
        } else {
            section.classList.remove('expanded');
            setTimeout(() => section.style.display = 'none', 300);
        }
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function updateDevilFruitHotkey() {
    try {
        const hotkey = document.getElementById('devilFruitHotkeyDropdown').value;
        await pywebview.api.update_devil_fruit_hotkey(hotkey);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function updateLoopsPerPurchase() {
    try {
        const loops = parseInt(document.getElementById('loopsPerPurchaseInput').value);
        await pywebview.api.update_loops_per_purchase(loops);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function toggleCraftLegBait() {
    try {
        const enabled = document.getElementById('craftLegBaitToggle').checked;
        const setPointBtn = document.getElementById('legBaitSetPointBtn');
        setPointBtn.disabled = !enabled;
        await pywebview.api.toggle_craft_leg_bait(enabled);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function toggleCraftRareBait() {
    try {
        const enabled = document.getElementById('craftRareBaitToggle').checked;
        const setPointBtn = document.getElementById('rareBaitSetPointBtn');
        setPointBtn.disabled = !enabled;
        await pywebview.api.toggle_craft_rare_bait(enabled);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function setLegBaitPoint() {
    const checkbox = document.getElementById('craftLegBaitToggle');
    if (!checkbox.checked) {
        return;
    }
    try {
        const initialState = await pywebview.api.get_state();
        const oldPoint = JSON.stringify(initialState.leg_bait_point);
        await pywebview.api.set_leg_bait_point();
        
        let attempts = 0;
        const pollInterval = setInterval(async () => {
            const state = await pywebview.api.get_state();
            const newPoint = JSON.stringify(state.leg_bait_point);
            if (newPoint !== oldPoint || attempts++ > 150) {
                clearInterval(pollInterval);
                updatePointDisplay('legBaitPointDisplay', state.leg_bait_point);
            }
        }, 200);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function setRareBaitPoint() {
    const checkbox = document.getElementById('craftRareBaitToggle');
    if (!checkbox.checked) {
        return;
    }
    try {
        const initialState = await pywebview.api.get_state();
        const oldPoint = JSON.stringify(initialState.rare_bait_point);
        await pywebview.api.set_rare_bait_point();
        
        let attempts = 0;
        const pollInterval = setInterval(async () => {
            const state = await pywebview.api.get_state();
            const newPoint = JSON.stringify(state.rare_bait_point);
            if (newPoint !== oldPoint || attempts++ > 150) {
                clearInterval(pollInterval);
                updatePointDisplay('rareBaitPointDisplay', state.rare_bait_point);
            }
        }, 200);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function updateAdvancedTiming() {
    try {
        const params = {
            pre_cast_e_delay: parseFloat(document.getElementById('preCastEDelayInput').value),
            pre_cast_click_delay: parseFloat(document.getElementById('preCastClickDelayInput').value),
            pre_cast_type_delay: parseFloat(document.getElementById('preCastTypeDelayInput').value),
            pre_cast_anti_detect_delay: parseFloat(document.getElementById('preCastAntiDetectDelayInput').value),
            auto_select_bait_delay: parseFloat(document.getElementById('autoSelectBaitDelayInput').value),
            store_fruit_hotkey_delay: parseFloat(document.getElementById('storeFruitHotkeyDelayInput').value),
            store_fruit_click_delay: parseFloat(document.getElementById('storeFruitClickDelayInput').value),
            store_fruit_shift_delay: parseFloat(document.getElementById('storeFruitShiftDelayInput').value),
            store_fruit_backspace_delay: parseFloat(document.getElementById('storeFruitBackspaceDelayInput').value),
            craft_nav_key_1: document.getElementById('craftNavKey1Input').value.toLowerCase(),
            craft_nav_duration_1: parseFloat(document.getElementById('craftNavDuration1Input').value),
            craft_nav_key_2: document.getElementById('craftNavKey2Input').value.toLowerCase(),
            craft_nav_duration_2: parseFloat(document.getElementById('craftNavDuration2Input').value),
            craft_nav_key_3: document.getElementById('craftNavKey3Input').value.toLowerCase(),
            craft_nav_duration_3: parseFloat(document.getElementById('craftNavDuration3Input').value),
            craft_nav_key_4: document.getElementById('craftNavKey4Input').value.toLowerCase(),
            craft_nav_duration_4: parseFloat(document.getElementById('craftNavDuration4Input').value),
            craft_nav_wait_delay: parseFloat(document.getElementById('craftNavWaitDelayInput').value),
            craft_t_press_delay: parseFloat(document.getElementById('craftTPressDelayInput').value),
            craft_click_delay: parseFloat(document.getElementById('craftClickDelayInput').value),
            craft_button_delay: parseFloat(document.getElementById('craftButtonDelayInput').value),
            craft_craft_button_delay: parseFloat(document.getElementById('craftCraftButtonDelayInput').value),
            craft_sequence_delay: parseFloat(document.getElementById('craftSequenceDelayInput').value),
            craft_exit_delay: parseFloat(document.getElementById('craftExitDelayInput').value),
            rod_select_delay: parseFloat(document.getElementById('rodSelectDelayInput').value),
            cursor_anti_detect_delay: parseFloat(document.getElementById('cursorAntiDetectDelayInput').value),
            scan_loop_delay: parseFloat(document.getElementById('scanLoopDelayInput').value),
            pd_approaching_damping: parseFloat(document.getElementById('pdApproachingDampingInput').value),
            pd_chasing_damping: parseFloat(document.getElementById('pdChasingDampingInput').value),
            gap_tolerance_multiplier: parseFloat(document.getElementById('gapToleranceMultiplierInput').value)
        };
        
        await pywebview.api.update_advanced_timing(params);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function toggleWebhookOption(option) {
    try {
        let toggleId;
        if (option === 'devil_fruit') {
            toggleId = 'webhookDevilFruitToggle';
        } else if (option === 'purchase') {
            toggleId = 'webhookPurchaseToggle';
        } else if (option === 'recovery') {
            toggleId = 'webhookRecoveryToggle';
        }
        
        const enabled = document.getElementById(toggleId).checked;
        const webhookPingsEnabled = document.getElementById('webhookPingsToggle')?.checked ?? true;
        
        if (typeof pywebview !== 'undefined') {
            await pywebview.api.set_webhook_option(option, enabled && webhookPingsEnabled);
        }
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function toggleWebhookPings() {
    try {
        const enabled = document.getElementById('webhookPingsToggle').checked;
        
        const devilFruitEnabled = document.getElementById('webhookDevilFruitToggle')?.checked ?? false;
        const purchaseEnabled = document.getElementById('webhookPurchaseToggle')?.checked ?? false;
        const recoveryEnabled = document.getElementById('webhookRecoveryToggle')?.checked ?? false;
        
        if (typeof pywebview !== 'undefined') {
            await pywebview.api.set_webhook_option('devil_fruit', devilFruitEnabled && enabled);
            await pywebview.api.set_webhook_option('purchase', purchaseEnabled && enabled);
            await pywebview.api.set_webhook_option('recovery', recoveryEnabled && enabled);
        }
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function toggleMinimizeOnRun() {
    try {
        const enabled = document.getElementById('minimizeToggle').checked;
        
        if (typeof pywebview !== 'undefined') {
            await pywebview.api.set_minimize_on_run(enabled);
        }
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function toggleStayOnTop() {
    try {
        const enabled = document.getElementById('stayOnTopToggle').checked;
        
        if (typeof pywebview !== 'undefined') {
            await pywebview.api.set_stay_on_top(enabled);
        }
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function saveWebhookSettings() {
    try {
        const btn = event.target;
        const originalText = btn.textContent;
        const url = document.getElementById('webhookUrlInput').value.trim();
        const userId = document.getElementById('discordUserIdInput').value.trim();
        
        btn.disabled = true;
        btn.textContent = 'Saving...';
        
        await pywebview.api.update_webhook_url(url);
        await pywebview.api.update_discord_user_id(userId);
        
        btn.textContent = 'Saved';
        btn.style.background = 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.2))';
        btn.style.borderColor = 'rgba(16, 185, 129, 0.4)';
        
        setTimeout(() => {
            btn.disabled = false;
            btn.textContent = originalText;
            btn.style.background = '';
            btn.style.borderColor = '';
        }, 2000);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

async function testWebhook() {
    try {
        const btn = event.target;
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Testing...';
        
        const result = await pywebview.api.test_webhook();
        
        if (result.success) {
            btn.textContent = 'Success';
            btn.style.background = 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.2))';
            btn.style.borderColor = 'rgba(16, 185, 129, 0.4)';
        } else {
            btn.textContent = 'Failed: ' + result.message;
            btn.style.background = 'linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(220, 38, 38, 0.2))';
            btn.style.borderColor = 'rgba(239, 68, 68, 0.4)';
        }
        
        setTimeout(() => {
            btn.disabled = false;
            btn.textContent = originalText;
            btn.style.background = '';
            btn.style.borderColor = '';
        }, 3000);
    } catch (error) {
        console.error('Error: ' + error);
    }
}

function minimizeWindow() {
    if (window.pywebview && window.pywebview.api) {
        pywebview.api.minimize_window();
    }
}

function maximizeWindow() {
    if (window.pywebview && window.pywebview.api) {
        pywebview.api.toggle_maximize();
    }
}

function closeWindow() {
    if (window.pywebview && window.pywebview.api) {
        pywebview.api.close_window();
    }
}

function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    if (isError) {
        toast.style.background = 'linear-gradient(135deg, rgba(45, 45, 49, 0.98), rgba(35, 35, 38, 0.98))';
        toast.style.border = '1px solid rgba(255, 255, 255, 0.1)';
    } else {
        toast.style.background = 'linear-gradient(135deg, rgba(45, 45, 49, 0.98), rgba(35, 35, 38, 0.98))';
        toast.style.border = '1px solid rgba(255, 255, 255, 0.1)';
    }
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

let previousTab = 'dashboard';
let advancedWarningShown = false;
let countdownTimer = null;

document.addEventListener('DOMContentLoaded', function() {
    const navItems = document.querySelectorAll('.nav-item');
    const views = document.querySelectorAll('.view');
    
    navItems.forEach(item => {
        item.addEventListener('click', function() {
            const viewName = this.getAttribute('data-view');
            
            if (viewName === 'advanced' && !advancedWarningShown) {
                const currentActive = document.querySelector('.nav-item.active');
                if (currentActive) {
                    previousTab = currentActive.getAttribute('data-view');
                }
                
                navItems.forEach(nav => nav.classList.remove('active'));
                this.classList.add('active');
                views.forEach(view => view.classList.remove('active'));
                document.getElementById(viewName).classList.add('active');
                
                showAdvancedWarning();
                return;
            }
            
            if (viewName !== 'advanced') {
                previousTab = viewName;
            }
            
            navItems.forEach(nav => nav.classList.remove('active'));
            this.classList.add('active');
            
            views.forEach(view => view.classList.remove('active'));
            document.getElementById(viewName).classList.add('active');
        });
    });
});

function showAdvancedWarning() {
    const warning = document.getElementById('advancedWarning');
    const content = document.getElementById('advancedContent');
    const proceedBtn = document.getElementById('advancedProceedBtn');
    const countdownSpan = document.getElementById('advancedCountdown');
    
    warning.style.display = 'block';
    content.style.display = 'none';
    
    let countdown = 5;
    countdownSpan.textContent = countdown;
    proceedBtn.disabled = true;
    proceedBtn.style.opacity = '0.5';
    proceedBtn.style.cursor = 'not-allowed';
    
    if (countdownTimer) clearInterval(countdownTimer);
    
    countdownTimer = setInterval(() => {
        countdown--;
        if (countdown > 0) {
            countdownSpan.textContent = countdown;
        } else {
            clearInterval(countdownTimer);
            proceedBtn.disabled = false;
            proceedBtn.style.opacity = '1';
            proceedBtn.style.cursor = 'pointer';
            proceedBtn.innerHTML = "I know what I'm doing";
        }
    }, 1000);
}

function closeAdvancedWarning() {
    if (countdownTimer) clearInterval(countdownTimer);
    
    const navItems = document.querySelectorAll('.nav-item');
    const views = document.querySelectorAll('.view');
    
    navItems.forEach(nav => nav.classList.remove('active'));
    views.forEach(view => view.classList.remove('active'));
    
    const previousNavItem = document.querySelector(`.nav-item[data-view="${previousTab}"]`);
    if (previousNavItem) {
        previousNavItem.classList.add('active');
        document.getElementById(previousTab).classList.add('active');
    }
}

function proceedToAdvanced() {
    if (countdownTimer) clearInterval(countdownTimer);
    
    advancedWarningShown = true;
    const warning = document.getElementById('advancedWarning');
    const content = document.getElementById('advancedContent');
    
    warning.style.display = 'none';
    content.style.display = 'none';
    
    setTimeout(() => {
        content.style.display = 'block';
    }, 10);
}

function showResetConfirmation() {
    const overlay = document.getElementById('resetConfirmation');
    const dialog = document.getElementById('resetDialog');
    overlay.style.display = 'flex';
    
    setTimeout(() => {
        overlay.style.background = 'rgba(32, 32, 32, 0.98)';
        dialog.style.opacity = '1';
        dialog.style.transform = 'translateY(0) scale(1)';
    }, 10);
}

function closeResetConfirmation() {
    const overlay = document.getElementById('resetConfirmation');
    const dialog = document.getElementById('resetDialog');
    
    overlay.style.background = 'rgba(32, 32, 32, 0)';
    dialog.style.opacity = '0';
    dialog.style.transform = 'translateY(-20px) scale(0.95)';
    
    setTimeout(() => {
        overlay.style.display = 'none';
    }, 300);
}

async function confirmReset() {
    try {
        closeResetConfirmation();
        const result = await pywebview.api.reset_to_defaults();
        if (result.success) {
            showToast('✅ Advanced settings reset to defaults', 'success');
            setTimeout(() => {
                initializeUI();
            }, 500);
        } else {
            showToast('❌ Failed to reset settings', 'error');
        }
    } catch (error) {
        console.error('Reset error:', error);
        showToast('❌ Error: ' + error, 'error');
    }
}

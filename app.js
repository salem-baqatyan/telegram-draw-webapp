// app.js

/**
 * وظائف لوحة الرسم مع دمج Telegram WebApp
 * (تم تكييفه بناءً على نموذجك وربطه بـ IDs تصميمك)
 */
(() => {
    // #1. تهيئة Telegram WebApp
    const tg = window.Telegram?.WebApp || null;

// #2. محددات DOM
    const mainCanvas = document.getElementById('mainCanvas');
    const tempCanvas = document.getElementById('tempCanvas'); 
    const wordBox = document.querySelector('.word');
    const btnPencil = document.getElementById('toolPencil');
    const btnEraser = document.getElementById('toolEraser');
    const btnFill = document.getElementById('toolFill');
    const btnUndo = document.getElementById('btnUndo');
    const btnRedo = document.getElementById('btnRedo');    
    const btnClear = document.getElementById('btnClear');
    const btnShapes = document.getElementById('toolShapes'); 
    const shapeDialog = document.getElementById('shapeDialog'); 
    const shapeOptions = document.getElementById('shapeOptions'); 
    const shapeIconContainer = btnShapes?.querySelector('.svg');   
    const btnSend = document.getElementById('btnSend');
    const brushSizeControl = document.getElementById('brushSizeControl');
    const brushInfo = brushSizeControl?.querySelector('.brush-info');
    const brushCircle = brushSizeControl?.querySelector('div[style*="border-radius: 50%"]');
    
    // 🎨 المدخل الجديد لزر الألوان
    const colorInput = document.getElementById('colorInput');
    const colorIconSpan = document.getElementById('colorIconSpan');
    
    // التأكد من وجود اللوحات
    if (!mainCanvas || !tempCanvas) {
        console.error('Canvas elements not found! Please ensure mainCanvas and tempCanvas have the correct ID.');
        return;
    }

    const mainCtx = mainCanvas.getContext('2d', { alpha: false }); // سياق الرسم الأساسي (الرسم الدائم)
    const tempCtx = tempCanvas.getContext('2d', { alpha: true });  // سياق الرسم المؤقت (لحركة الماوس/اللمس)
    
    // #3. State
    let drawing = false;
    let tool = 'brush'; 
    let brushSize = 10; 
    let brushColor = '#000000'; // القيمة الافتراضية
    let last = { x: 0, y: 0 };
    const undoStack = [];
    const redoStack = []; 
    const MAX_UNDO = 20;
    let brushOpacity = 1.0; // 1.0 = 100% (كاملة)
    let shapeStart = { x: 0, y: 0 };
    let selectedShape = null;
    

    // 🎯 ثوابت SVG لأيقونات الأشكال
const SHAPE_ICON_DEFAULT = `<svg fill="currentColor" version="1.1" id="Icons" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"viewBox="0 0 32 32" xml:space="preserve"><g><path d="M22,29c-4.4,0-8-3.6-8-8s3.6-8,8-8s8,3.6,8,8S26.4,29,22,29z"/></g><path d="M12,21c0-3.5,1.8-6.5,4.4-8.3l-3-4.4C12.9,7.5,12,7,11,7S9.1,7.5,8.6,8.3l-6,8.9c-0.7,1-0.7,2.2-0.2,3.2C2.9,21.4,3.9,22,5,22h7.1C12,21.7,12,21.3,12,21z"/><path d="M25,4h-8c-1.4,0-2.5,0.9-2.9,2.1c0.4,0.3,0.7,0.6,0.9,1l3.1,4.6c1.2-0.5,2.5-0.8,3.8-0.8c2.3,0,4.3,0.8,6,2V7C28,5.3,26.7,4,25,4z"/>svg>`;

const SHAPE_ICON_SQUARE = `<svg width="24" height="24" viewBox="0 0 15 15" fill="currentColor" xmlns="http://www.w3.org/2000/svg" style="height: 24px; width: 24px"><path fill-rule="evenodd" clip-rule="evenodd" d="M1 1H1.5H13.5H14V1.5V13.5V14H13.5H1.5H1V13.5V1.5V1ZM2 2V13H13V2H2Z" /></svg>`;

const SHAPE_ICON_CIRCLE = `<svg width="24" height="24" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" style="height: 24px; width: 24px"><circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="4" fill="none"/></svg>`;

const SHAPE_ICON_TRIANGLE = `<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="miter" style="height: 24px; width: 24px"><polygon points="12 3 2.5 21 21.5 21 12 3" fill="none"></polygon></svg>`;

// دالة مساعدة لتحديث الأيقونة
function updateShapeIcon(shapeType) {
    const shapeIconContainer = btnShapes?.querySelector('.svg');
    if (!shapeIconContainer) return;

    let iconHtml = SHAPE_ICON_DEFAULT;
    if (shapeType === 'square') iconHtml = SHAPE_ICON_SQUARE;
    else if (shapeType === 'circle') iconHtml = SHAPE_ICON_CIRCLE;
    else if (shapeType === 'triangle') iconHtml = SHAPE_ICON_TRIANGLE;

    shapeIconContainer.innerHTML = iconHtml;
}
    

    // ****************************
    // #4. وظائف الدعم
    // ****************************

    /**
     * @description تهيئة وضبط حجم اللوحات وملء الخلفية باللون الأبيض.
     */
    function fixCanvas() {
        const ratio = window.devicePixelRatio || 1;
        // نستخدم الأبعاد الثابتة 800x800 كما هي محددة في HTML
        const size = 500; 

        // ضبط الأبعاد الحقيقية للـ mainCanvas
        mainCanvas.width = size * ratio;
        mainCanvas.height = size * ratio;
        mainCtx.setTransform(ratio, 0, 0, ratio, 0, 0);

        // ضبط الأبعاد الحقيقية للـ tempCanvas
        tempCanvas.width = size * ratio;
        tempCanvas.height = size * ratio;
        tempCtx.setTransform(ratio, 0, 0, ratio, 0, 0);

        // ✅ الحل: ملء الخلفية باللون الأبيض على mainCanvas
        mainCtx.fillStyle = '#ffffff';
        mainCtx.fillRect(0, 0, mainCanvas.width / ratio, mainCanvas.height / ratio);
    }
    
// تحديث مؤشر الفرشاة المرئي
function updateBrushIndicator(size, opacity) {
    const opacityPercent = Math.round(opacity * 100);
    
    if (brushCircle) {
        // 🎯 الحل: نستخدم حجم المؤشر (size) مباشرةً، ونطبق الشفافية
        brushCircle.style.width = size + 'px';
        brushCircle.style.height = size + 'px';
        brushCircle.style.opacity = opacity; // تطبيق الشفافية على المؤشر
    }
    if (brushInfo) {
        // 🎯 عرض الشفافية الجديدة
        brushInfo.innerHTML = `${Math.round(size)}px<br/>${opacityPercent}%`;
    }
}


// حفظ حالة الرسم للتراجع
function pushUndo() {
    try {
        if (undoStack.length >= MAX_UNDO) undoStack.shift();
        undoStack.push(mainCanvas.toDataURL('image/png'));
        // 🎯 التعديل: مسح مكدس الإعادة عند أي حركة رسم جديدة
        redoStack.length = 0; 
    } catch (e) { console.warn('undo push failed', e); }
}

// التراجع عن آخر خطوة
function doUndo() {
    // الشرط: يجب أن يكون هناك أكثر من حالة واحدة في مكدس التراجع.
    // الحالة 0 هي دائما الخلفية البيضاء التي يجب أن تبقى.
    if (undoStack.length <= 1) { 
        // إذا كان المكدس فارغًا (0) أو يحتوي على حالة البداية فقط (1)، نتوقف.
        return; 
    }
    
    // سحب الحالة الحالية (N) وتخزينها في مكدس الإعادة 
    // (هنا يتم سحب آخر حالة رسم فعليًا).
    const undoneState = undoStack.pop(); 
    redoStack.push(undoneState); 
    
    // تطبيق الحالة السابقة مباشرة (N-1)
    const dataToApply = undoStack[undoStack.length - 1]; 
    
    const i = new Image();
    i.onload = () => {
        mainCtx.clearRect(0, 0, mainCanvas.width, mainCanvas.height);
        mainCtx.drawImage(i, 0, 0, mainCanvas.width / (window.devicePixelRatio || 1), mainCanvas.height / (window.devicePixelRatio || 1));
    };
    i.src = dataToApply;
}

// 🎯 الجديد: الإعادة إلى آخر خطوة تم التراجع عنها
function doRedo() {
    if (!redoStack.length) return;
    
    const data = redoStack.pop(); // استرداد الحالة من مكدس الإعادة
    undoStack.push(data); // إعادتها إلى مكدس التراجع
    
    const i = new Image();
    i.onload = () => {
        mainCtx.clearRect(0, 0, mainCanvas.width, mainCanvas.height);
        mainCtx.drawImage(i, 0, 0, mainCanvas.width / (window.devicePixelRatio || 1), mainCanvas.height / (window.devicePixelRatio || 1));
    };
    i.src = data;
}

/**
 * @description تحويل اللون الست عشري (#RRGGBB) إلى مصفوفة RGB (مع الشفافية 255).
 */
function hexToRgb(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return [r, g, b, 255]; // 255 للـ Alpha (الشفافية الكاملة)
}

function floodFill(startX, startY) {
    pushUndo(); // حفظ الحالة قبل التعبئة
    const ratio = window.devicePixelRatio || 1;
    
    // تصحيح الإحداثيات بالنسبة لـ Canvas (800x800)
    // ⚠️ يتم تصحيح الإحداثيات هنا بالنسبة للـ ratio
    const x = Math.round(startX * ratio);
    const y = Math.round(startY * ratio);

    const ctx = mainCtx;
    const canvasWidth = mainCanvas.width;
    const canvasHeight = mainCanvas.height;
    
    // التأكد من أن الإحداثيات ضمن حدود Canvas
    if (x < 0 || x >= canvasWidth || y < 0 || y >= canvasHeight) return;

    // 1. الحصول على بيانات الصورة الحالية
    const imgData = ctx.getImageData(0, 0, canvasWidth, canvasHeight);
    const data = imgData.data;

    // 2. الحصول على اللون المستهدف (اللون عند النقر)
    const pixelIndex = (y * canvasWidth + x) * 4;
    const targetColor = [
        data[pixelIndex],
        data[pixelIndex + 1],
        data[pixelIndex + 2],
        data[pixelIndex + 3]
    ];
    
    // 3. الحصول على اللون الجديد (لون الفرشاة)
    const fillColor = hexToRgb(brushColor);

    // إذا كان اللون المستهدف هو نفس اللون الجديد، لا تفعل شيئًا
    if (targetColor.every((val, i) => val === fillColor[i])) return;

    const stack = [[x, y]];

    function getPixelColor(px, py) {
        const i = (py * canvasWidth + px) * 4;
        // يجب التحقق من الحدود هنا أيضًا لسلامة الكود
        if (i < 0 || i + 3 >= data.length) return [0, 0, 0, 0]; 
        return [data[i], data[i + 1], data[i + 2], data[i + 3]];
    }

    function setPixelColor(px, py) {
        const i = (py * canvasWidth + px) * 4;
        data[i] = fillColor[0];
        data[i + 1] = fillColor[1];
        data[i + 2] = fillColor[2];
        data[i + 3] = fillColor[3]; 
    }
    
    function colorsMatch(c1, c2) {
        return c1[0] === c2[0] && c1[1] === c2[1] && c1[2] === c2[2] && c1[3] === c2[3];
    }

    // 4. خوارزمية التعبئة (Stack-based)
    while (stack.length) {
        const [cx, cy] = stack.pop();

        if (cx < 0 || cx >= canvasWidth || cy < 0 || cy >= canvasHeight) continue;
        
        const currentColor = getPixelColor(cx, cy);

        // إذا كان اللون الحالي هو اللون المستهدف، قم بالتعبئة وادفع الجيران
        if (colorsMatch(currentColor, targetColor)) {
            setPixelColor(cx, cy);
            
            // دفع الجيران (فوق، تحت، يسار، يمين)
            stack.push([cx + 1, cy]);
            stack.push([cx - 1, cy]);
            stack.push([cx, cy + 1]);
            stack.push([cx, cy - 1]);
        }
    }

    // 5. وضع البيانات المحدثة على Canvas
    ctx.putImageData(imgData, 0, 0);
}


    // ****************************
    // #5. وظائف الرسم
    // ****************************

    // الحصول على موقع الماوس/اللمس
function getPos(e) {
    // نستخدم tempCanvas لأنها هي التي تستقبل الأحداث
    const rect = tempCanvas.getBoundingClientRect(); 
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    
    // إحداثيات CSS غير المصححة
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    
    // 🎯 العودة إلى إحداثيات CSS التي يجب أن تستخدم في دالة الرسم
    return { x, y }; 
}

// بدء الرسم (Mouse Down / Touch Start)
function startDraw(e) {
    if (!e.target.closest('.canvas-container')) return;

    if (tool === 'fill') {
        const pos = getPos(e);
        floodFill(pos.x, pos.y);        
        e.preventDefault();
        return; 
    }        
        
    // 🎯 منطق بدء رسم الشكل
    if (tool === 'shape') {
        drawing = true;
        shapeStart = getPos(e); // حفظ نقطة البداية
        tempCtx.clearRect(0, 0, tempCanvas.width, tempCanvas.height); // مسح اللوحة المؤقتة
        e.preventDefault();
        return;
    }

    drawing = true;
    last = getPos(e);

// 1. إعداد السياق المشترك (الحجم، الأطراف، الشفافية)
    const mainContext = mainCtx;
    const tempContext = tempCtx;
    
    // الإعدادات المشتركة
    mainContext.lineCap = 'round';
    mainContext.lineJoin = 'round';
    // 🎯 ملاحظة: brushSize * 1.5 هو عامل تصحيح الحجم الذي تستخدمه
    mainContext.lineWidth = brushSize; 
    mainContext.globalAlpha = brushOpacity;
    
    tempContext.lineCap = 'round';
    tempContext.lineJoin = 'round';
    tempContext.lineWidth = brushSize; 
    tempContext.globalAlpha = brushOpacity;

    // 2. منطق المسح (Eraser)
if (tool === 'eraser') {
    // 🎯 التعديل: نستخدم source-over واللون الأبيض للرسم الدائم (المسح)
    mainContext.globalCompositeOperation = 'source-over';
    mainContext.strokeStyle = '#ffffff'; 
    
    // رسم النقطة الفعلية (المسح/الصبغ بالأبيض) على اللوحة الرئيسية
    mainContext.beginPath();
    mainContext.moveTo(last.x, last.y);
    mainContext.lineTo(last.x, last.y);
    mainContext.stroke();
    
    // المؤشر المرئي على tempCanvas (لتظهر النقطة بيضاء للمستخدم)
    tempContext.globalCompositeOperation = 'source-over';
    tempContext.strokeStyle = '#ffffff'; 
    tempContext.beginPath();
    tempContext.moveTo(last.x, last.y);
    tempContext.lineTo(last.x, last.y);
    tempContext.stroke();
    
}

    // 3. منطق الفرشاة (Brush)
    else if (tool === 'brush') {
        // استخدام source-over للرسم الدائم (الفرشاة)
        mainContext.globalCompositeOperation = 'source-over';
        mainContext.strokeStyle = brushColor;
        
        // رسم النقطة الفعلية على اللوحة الرئيسية
        mainContext.beginPath();
        mainContext.moveTo(last.x, last.y);
        mainContext.lineTo(last.x, last.y);
        mainContext.stroke();
        
        // المؤشر المرئي على tempCanvas (بنفس لون الفرشاة)
        tempContext.globalCompositeOperation = 'source-over';
        tempContext.strokeStyle = brushColor;
        tempContext.beginPath();
        tempContext.moveTo(last.x, last.y);
        tempContext.lineTo(last.x, last.y);
        tempContext.stroke();
    }
    
    // 4. إعادة تعيين الإعدادات العامة (مهم بعد المسح/الرسم)
    mainContext.globalCompositeOperation = 'source-over';
    mainContext.globalAlpha = 1.0;

    // مسح tempCtx قبل أن نبدأ الرسم عليها في onMove
    tempCtx.clearRect(0, 0, tempCanvas.width, tempCanvas.height); 

    e.preventDefault();
}

// إيقاف الرسم (Mouse Up / Touch End)
function stopDraw(e) {
    if (!drawing) return;
if (tool === 'shape') {
        drawing = false;
        const p = getPos(e); 
        drawShape(mainCtx, shapeStart.x, shapeStart.y, p.x, p.y, selectedShape);
        pushUndo();
        tempCtx.clearRect(0, 0, tempCanvas.width, tempCanvas.height); 
        e && e.preventDefault();
        return;
    }
    drawing = false;
    
    // 🎯 الحل: حفظ حالة اللوحة (Undo) بعد اكتمال سحب الخط
    pushUndo(); 
    
    // مسح اللوحة المؤقتة (tempCanvas) فقط
    tempCtx.clearRect(0, 0, tempCanvas.width, tempCanvas.height); 
    
    e && e.preventDefault();
}
    
    
    // الحركة أثناء الرسم
function onMove(e) {
    if (!drawing) return;
    const p = getPos(e);

if (tool === 'shape') {
        tempCtx.clearRect(0, 0, tempCanvas.width, tempCanvas.height); 
        drawShape(tempCtx, shapeStart.x, shapeStart.y, p.x, p.y, selectedShape);
        e.preventDefault();
        return;
    }
    
    // 1. مسح اللوحة المؤقتة قبل رسم الخط الجديد
    tempCtx.clearRect(0, 0, tempCanvas.width, tempCanvas.height); 

    // 2. تطبيق المسح/الرسم على mainCanvas بشكل مباشر (العمل الفعلي والدائم)
    const mainContext = mainCtx;
    
    mainContext.lineCap = 'round';
    mainContext.lineJoin = 'round';
    mainContext.lineWidth = brushSize;
    mainContext.globalAlpha = brushOpacity;
    
    if (tool === 'eraser') {
        // المسح الفعلي: يستخدم destination-out على اللوحة الرئيسية (mainCtx)
    mainContext.globalCompositeOperation = 'source-over';
    mainContext.strokeStyle = '#ffffff';    
    } else {
        // القلم الفعلي: يستخدم source-over واللون المختار
        mainContext.globalCompositeOperation = 'source-over';
        mainContext.strokeStyle = brushColor;
    }
    
    mainContext.beginPath();
    mainContext.moveTo(last.x, last.y);
    mainContext.lineTo(p.x, p.y);
    mainContext.stroke();
    
    // 3. 💡 المؤشر المرئي على اللوحة المؤقتة (tempCtx)
    const tempContext = tempCtx;
    
    tempContext.lineCap = 'round';
    tempContext.lineJoin = 'round';
    tempContext.lineWidth = brushSize;
    
    // 🎯 التعديل الحاسم: تعيين اللون الأبيض بشكل قسري للممحاة هنا
    tempContext.globalAlpha = brushOpacity;
    tempContext.globalCompositeOperation = 'source-over'; 
    tempContext.strokeStyle = (tool === 'eraser') ? '#ffffff' : brushColor;
    
    tempContext.beginPath();
    tempContext.moveTo(last.x, last.y);
    tempContext.lineTo(p.x, p.y);
    tempContext.stroke();
    
    // 4. إعادة الوضع إلى source-over لـ mainCtx بعد اكتمال المسح/الرسم
    mainContext.globalAlpha = 1.0;
    mainContext.globalCompositeOperation = 'source-over'; 

    last = p;
    e.preventDefault();
}

// 🎯 الجديد: دالة لرسم شكل محدد
function drawShape(ctx, startX, startY, endX, endY, shapeType) {
    const width = endX - startX;
    const height = endY - startY;
    
    ctx.lineCap = 'butt'; 
    ctx.lineJoin = 'miter'; 
    
    // تطبيق إعدادات الفرشاة (باستخدام عامل التصحيح 1.5)
    ctx.lineWidth = brushSize; 
    ctx.strokeStyle = brushColor;
    ctx.globalAlpha = brushOpacity;
    
    ctx.beginPath();

    if (shapeType === 'square') {
        ctx.rect(startX, startY, width, height); 
    } else if (shapeType === 'circle') {
        const radiusX = Math.abs(width) / 2;
        const radiusY = Math.abs(height) / 2;
        const centerX = startX + width / 2;
        const centerY = startY + height / 2;
        ctx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, 2 * Math.PI);
    } else if (shapeType === 'triangle') {
        ctx.moveTo(startX + width / 2, startY); // القمة
        ctx.lineTo(startX, startY + height); // اليسار السفلي
        ctx.lineTo(startX + width, startY + height); // اليمين السفلي
        ctx.closePath();
    }
    
    ctx.stroke(); 

    // إعادة الشفافية إلى القيمة الافتراضية
    ctx.globalAlpha = 1.0;
}

    // وظيفة التعبئة (Fill)


// ****************************
// #6. وظيفة الإرسال إلى Telegram (مربوطة بزر الحفظ)
// ****************************
function sendToTelegram() {
    // ⚠️ نستخدم 'tg' المعرف في النطاق الخارجي (الجزء #1)
    if (!tg) { 
        alert('⚠️ لم يتم اكتشاف بيئة تيليجرام.');
        return;
    }
    
    // منع النقر المزدوج أثناء الرفع
    btnSend.removeEventListener('click', sendToTelegram);

    // مفتاح API الخاص بك من ImgBB
    const IMGBB_API_KEY = "adcb6daec9bef4d4d64dc34f2f8ca568"; // يُفضل وضع مفتاحك الحقيقي هنا
    
    // 1. استخراج الصورة من mainCanvas
    const dataURL = mainCanvas.toDataURL('image/jpeg', 0.8);
    const base64Image = dataURL.replace(/^data:image\/[^;]+;base64,/, '');

    // 2. إظهار حالة التحميل
    tg.MainButton.setText('جاري الرفع...').show().disable();
    tg.HapticFeedback?.impactOccurred('medium');

    // 3. رفع الصورة إلى ImgBB
    fetch(`https://api.imgbb.com/1/upload?key=${IMGBB_API_KEY}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: `image=${encodeURIComponent(base64Image)}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const imageUrl = data.data.url;
            
            // 4. إرسال رابط الصورة باستخدام البادئة المتوقعة من البوت
            const MESSAGE_PREFIX = "DOODLE_URL::"; 
            const messageToSend = MESSAGE_PREFIX + imageUrl;

            tg.sendData(messageToSend);
            
            tg.showAlert('✅ تم إرسال الرابط بنجاح إلى البوت!');
            
        } else {
            tg.showAlert('❌ فشل الرفع إلى ImgBB: ' + (data.error?.message || 'خطأ غير معروف.'));
        }
    })
    .catch(error => {
        tg.showAlert('❌ خطأ في الاتصال بالخادم (ImgBB): ' + error.message);
        console.error("Fetch Error:", error);
    })
    .finally(() => {
        // إعادة تفعيل الزر وإخفاء زر Telegram
        tg.MainButton.hide();
        btnSend.addEventListener('click', sendToTelegram); // إعادة معالج الحدث
    });
}


    // ****************************
    // #7. معالجات الأحداث (ربط أدوات التحكم)
    // ****************************

    // أحداث الرسم
    tempCanvas.addEventListener('mousedown', startDraw);
    tempCanvas.addEventListener('touchstart', startDraw, { passive: false });
    window.addEventListener('mouseup', stopDraw);
    window.addEventListener('touchend', stopDraw, { passive: false });
    tempCanvas.addEventListener('mousemove', onMove);
    tempCanvas.addEventListener('touchmove', onMove, { passive: false });

    // أحداث الأدوات وتحديث حالة 'active'
if (btnPencil) {
    btnPencil.addEventListener('click', () => {
        tool = 'brush';
        btnPencil.querySelector('.circle-switch').classList.add('active');
        btnEraser?.classList.remove('active');
        btnFill?.classList.remove('active');
        btnShapes?.classList.remove('active'); // 🎯 إلغاء تفعيل زر الأشكال

        selectedShape = null; // 🎯 إزالة الشكل المختار
        updateShapeIcon(selectedShape); // 🎯 إعادة الأيقونة إلى الافتراضي
    });
}

if (btnEraser) {
    btnEraser.addEventListener('click', () => {
        tool = 'eraser';
        btnEraser.classList.add('active');
        btnPencil?.querySelector('.circle-switch').classList.remove('active');
        btnFill?.classList.remove('active');
        btnShapes?.classList.remove('active'); // 🎯 إلغاء تفعيل زر الأشكال
        
        selectedShape = null; // 🎯 إزالة الشكل المختار
        updateShapeIcon(selectedShape); // 🎯 إعادة الأيقونة إلى الافتراضي
    });
}

if (btnFill) {
    btnFill.addEventListener('click', () => {
        tool = 'fill';
        btnFill.classList.add('active');
        btnPencil?.querySelector('.circle-switch').classList.remove('active');
        btnEraser?.classList.remove('active');
        btnShapes?.classList.remove('active'); // 🎯 إلغاء تفعيل زر الأشكال
        
        selectedShape = null; // 🎯 إزالة الشكل المختار
        updateShapeIcon(selectedShape); // 🎯 إعادة الأيقونة إلى الافتراضي
    });
}
    
    // التراجع والمسح
    if (btnUndo) btnUndo.addEventListener('click', () => doUndo());
    if (btnRedo) btnRedo.addEventListener('click', () => doRedo());
if (btnClear) {
    btnClear.addEventListener('click', () => {
        pushUndo(); // حفظ الحالة التي قبل المسح
        mainCtx.fillStyle = '#ffffff';
        mainCtx.fillRect(0, 0, mainCanvas.width / (window.devicePixelRatio || 1), mainCanvas.height / (window.devicePixelRatio || 1));
    });
}
if (btnShapes) {
    btnShapes.addEventListener('click', () => {
        // 1. تفعيل وضع الأشكال (لا نغير الأداة بعد، فقط نضعها في وضع الاستعداد)
        btnShapes.classList.add('active');
        btnPencil?.querySelector('.circle-switch').classList.remove('active');
        btnEraser?.classList.remove('active');
        btnFill?.classList.remove('active');

        // 2. عرض مربع حوار اختيار الشكل
        if (shapeDialog) {
            shapeDialog.style.display = 'block'; 
        }
    });
}
    
// 🎯 الجديد: منطق اختيار الشكل من داخل مربع الحوار
if (shapeOptions) {
    shapeOptions.addEventListener('click', (e) => {
        const shapeButton = e.target.closest('.shape-button');
        if (shapeButton) {
            const newShape = shapeButton.getAttribute('data-shape');
            selectedShape = newShape; // تحديث الشكل المختار
            tool = 'shape'; // الآن نضبط الأداة إلى 'shape'
            
            // 🎯 تحديث أيقونة زر الأشكال إلى الشكل المختار
            updateShapeIcon(newShape); 
            
            // إخفاء مربع الحوار
            if (shapeDialog) {
                 shapeDialog.style.display = 'none';
            }
            
            // تفعيل زر الأشكال وتجريد الأدوات الأخرى
            btnShapes?.classList.add('active');
            btnPencil?.querySelector('.circle-switch').classList.remove('active');
            btnEraser?.classList.remove('active');
            btnFill?.classList.remove('active');
        }
    });
}

// 🎯 الإضافة: إخفاء مربع الحوار عند النقر على Canvas
tempCanvas.addEventListener('mousedown', () => {
    if (shapeDialog && shapeDialog.style.display !== 'none' && tool !== 'shape') {
        // إخفاء مربع الحوار وإلغاء تفعيل زر الأشكال إذا لم يكن وضع الرسم مفعلاً
        shapeDialog.style.display = 'none';
        btnShapes?.classList.remove('active');
        tool = 'brush';
    }
});
    // الحفظ/الإرسال إلى Telegram
    if (btnSend) btnSend.addEventListener('click', sendToTelegram);

if (colorInput) {
        colorInput.addEventListener('input', (e) => {
            // تحديث لون الفرشاة عند اختيار لون جديد
            brushColor = e.target.value;
            
            // تحديث مؤشر الفرشاة ليعكس اللون الجديد (لون الخلفية)
            if (brushCircle) {
                 brushCircle.style.background = brushColor;
            }
            
            // تحديث لون أيقونة الألوان (خاصية color)
            if (colorIconSpan) {
                colorIconSpan.style.color = brushColor;
            }

        });
    }
    // ****************************
    // #8. منطق تغيير حجم الفرشاة (بالسحب العمودي)
    // ****************************
    
let isResizing = false;
let startY = 0;
let startX = 0; // 🎯 الجديد: إحداثيات بداية السحب الأفقي
let initialBrushSize = brushSize;
let initialBrushOpacity = brushOpacity; // 🎯 الجديد: قيمة الشفافية الابتدائية
    
if (brushSizeControl) {
    // أحداث الماوس للتحكم في الحجم والشفافية
    brushSizeControl.addEventListener('mousedown', (e) => {
        isResizing = true;
        startY = e.clientY;
        startX = e.clientX; // حفظ موضع X
        initialBrushSize = brushSize;
        initialBrushOpacity = brushOpacity;
        e.preventDefault();
    });
        window.addEventListener('mousemove', (e) => {
if (!isResizing) return;
        
        const deltaY = startY - e.clientY; // الحركة العمودية (للفرشاة)
        const deltaX = e.clientX - startX; // 🎯 الحركة الأفقية (للشفافية)
        
        // 1. التحكم في الحجم (الحد الأقصى 45)
        // يتم تقسيم دلتا Y على 2 لجعل الحركة أقل حساسية
        brushSize = Math.max(5, Math.min(45, initialBrushSize + deltaY / 2)); 
        
        // 2. التحكم في الشفافية (الحد الأقصى 1.0 = 100%)
        // تقسيم دلتا X على 300 لتحويل الحركة من بكسل إلى نسبة (300 بكسل = 100% تقريبا)
        let newOpacity = initialBrushOpacity + deltaX / 300; 
        
        // يجب أن تكون الشفافية بين 0.0 و 1.0
        brushOpacity = Math.max(0, Math.min(1.0, newOpacity));
        
        // 3. تحديث المؤشر
        updateBrushIndicator(brushSize, brushOpacity);
        
        e.preventDefault();
    });
    
    window.addEventListener('mouseup', () => {
        isResizing = false;
    });
    }
    
    // ****************************
    // #9. التهيئة (Initialization)
    // ****************************

    fixCanvas();
    pushUndo();
    updateBrushIndicator(brushSize, brushOpacity);
        
    // تفعيل أداة القلم بشكل افتراضي (لأنها الأداة الأساسية)
    btnPencil?.querySelector('.circle-switch')?.classList.add('active');
    
    // إدارة تغيير حجم النافذة
    window.addEventListener('resize', () => {
        const img = mainCanvas.toDataURL();
        fixCanvas();
        const i = new Image();
        i.onload = () => mainCtx.drawImage(i, 0, 0, mainCanvas.width / (window.devicePixelRatio||1), mainCanvas.height/(window.devicePixelRatio||1));
        i.src = img;
    });
if (brushCircle) {
        brushCircle.style.background = brushColor;
    }
    
    // تحديث لون أيقونة الألوان باللون الافتراضي عند التهيئة
    if (colorIconSpan) {
        colorIconSpan.style.color = brushColor;
    }
    // تهيئة Telegram WebApp وعرض الكلمة
try {
        if (tg) {
            tg.expand && tg.expand();
            const params = new URLSearchParams(window.location.search);
            let startWord = 'فطيرة ⚙️'; 
            if (params.has('word')) startWord = params.get('word');
            if (wordBox) wordBox.innerHTML = `${startWord} ⚙️`;

            // 🆕 إضافة منطق التصغير الشرطي هنا 
            // ----------------------------------------------------
            const canvasContainer = document.querySelector('.canvas-container');
            if (canvasContainer) {
                 // التحقق من أننا نعمل داخل التيليجرام 
                 // (عادةً ما يتم التحقق من وجود tg.WebApp)
                canvasContainer.classList.add('tg-scaled');
            }
            // ----------------------------------------------------

        }
    } catch(e){
        console.warn('init error', e);
    }

})();

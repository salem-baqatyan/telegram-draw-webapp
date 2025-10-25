
// Simple Canvas drawing + Telegram WebApp integration
(() => {
  const tg = window.Telegram?.WebApp || null;

  // DOM
    const mainCanvas = document.getElementById('main-canvas');
  const tempCanvas = document.getElementById('temp-canvas'); // <--- اللوحة الجديدة
  const mainCtx = mainCanvas.getContext('2d', { alpha: false }); // <--- السياق الرئيسي
  const tempCtx = tempCanvas.getContext('2d', { alpha: true }); // <--- سياق مؤقت (يجب أن يدعم الشفافية)
  const sizeInput = document.getElementById('size');
  const colorInput = document.getElementById('color');
  const sizeVal = document.getElementById('size-val');
  const btnBrush = document.getElementById('tool-brush');
  const btnEraser = document.getElementById('tool-eraser');
  const btnUndo = document.getElementById('undo');
  const btnClear = document.getElementById('clear');
  const btnDownload = document.getElementById('download');
  const btnSend = document.getElementById('btn-send');
  const wordBox = document.getElementById('word');
  const btnBack = document.getElementById('btn-back');

  // State
  let drawing = false;
  let tool = 'brush'; // or 'eraser'
  let brushSize = parseInt(sizeInput.value, 10);
  let brushColor = colorInput.value;
  let last = { x: 0, y: 0 };
  // Undo stack (store imageData URLs)
  const undoStack = [];
  const MAX_UNDO = 20;


  // Init canvas size to css pixel ratio for sharpness
function fixCanvas() {
    const ratio = window.devicePixelRatio || 1;
    const cssWidth = Math.min(800, Math.floor(window.innerWidth - 360));
    const size = Math.max(400, cssWidth);
    
    // تطبيق الأبعاد على mainCanvas
    mainCanvas.width = size * ratio;
    mainCanvas.height = size * ratio;
    mainCanvas.style.width = (size) + 'px';
    mainCanvas.style.height = (size) + 'px';
    mainCtx.setTransform(ratio, 0, 0, ratio, 0, 0);
    
    // تطبيق نفس الأبعاد على tempCanvas
    tempCanvas.width = size * ratio;
    tempCanvas.height = size * ratio;
    tempCanvas.style.width = (size) + 'px';
    tempCanvas.style.height = (size) + 'px';
    tempCtx.setTransform(ratio, 0, 0, ratio, 0, 0);

    // Background white على اللوحة الرئيسية فقط
    mainCtx.fillStyle = '#ffffff';
    mainCtx.fillRect(0,0,mainCanvas.width/ratio, mainCanvas.height/ratio);
    
    // مسح اللوحة المؤقتة (لضمان الشفافية)
    tempCtx.clearRect(0,0,tempCanvas.width/ratio, tempCanvas.height/ratio);
  }

fixCanvas();
  window.addEventListener('resize', () => {
    // حفظ ورسم من اللوحة الرئيسية فقط
    const img = mainCanvas.toDataURL();
    fixCanvas();
    const i = new Image();
    i.onload = () => mainCtx.drawImage(i, 0, 0, mainCanvas.width / (window.devicePixelRatio||1), mainCanvas.height/(window.devicePixelRatio||1));
    i.src = img;
  });

  // utilities
function doUndo() {
    if (!undoStack.length) {
      // مسح للوحة الرئيسية فقط
      mainCtx.fillStyle = '#ffffff';
      mainCtx.fillRect(0,0,mainCanvas.width,mainCanvas.height);
      return;
    }
    const data = undoStack.pop();
    const i = new Image();
    i.onload = () => {
      // استعادة الرسم للوحة الرئيسية
      mainCtx.clearRect(0,0,mainCanvas.width,mainCanvas.height);
      mainCtx.drawImage(i, 0, 0, mainCanvas.width/(window.devicePixelRatio||1), mainCanvas.height/(window.devicePixelRatio||1));
    };
    i.src = data;
  }

  // drawing
 function getPos(e) {
    // نستخدم tempCanvas للحصول على الإحداثيات لأنها التي تستقبل الحدث
    const rect = tempCanvas.getBoundingClientRect(); 
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
    const y = (e.touches ? e.touches[0].clientY : e.touches[0].clientY) - rect.top;
    return { x, y };
  }
function startDraw(e) {
    drawing = true;
    pushUndo();
    last = getPos(e);
    drawLine(last, last, tempCtx); // نرسم أول نقطة على اللوحة المؤقتة
    e.preventDefault();
  }
  function stopDraw(e) {
    if (!drawing) return;
    drawing = false;

    // 1. نسخ المحتوى من اللوحة المؤقتة إلى اللوحة الرئيسية
    // (نستخدم mainCtx هنا للرسم على اللوحة الرئيسية)
    mainCtx.drawImage(tempCanvas, 0, 0, mainCanvas.width/(window.devicePixelRatio||1), mainCanvas.height/(window.devicePixelRatio||1));

    // 2. مسح اللوحة المؤقتة استعدادًا للخطوة التالية
    tempCtx.clearRect(0, 0, tempCanvas.width, tempCanvas.height); 

    e && e.preventDefault();
  }

  // تم تعديلها لأخذ سياق الرسم كمعامل
  function drawLine(p1, p2, targetCtx) {
    targetCtx.lineCap = 'round';
    targetCtx.lineJoin = 'round';
    targetCtx.lineWidth = brushSize;
    if (tool === 'eraser') {
      // ملاحظة: الممحاة (destination-out) تعمل بشكل صحيح فقط على اللوحة الرئيسية
      // هنا نستخدمها للمعاينة، لكن عملية الدمج ستتولى الممحاة الفعلية
      targetCtx.globalCompositeOperation = 'source-over'; 
      targetCtx.strokeStyle = 'rgba(100,100,100,0.5)'; // معاينة شفافة للممحاة
    } else {
      targetCtx.globalCompositeOperation = 'source-over';
      targetCtx.strokeStyle = brushColor;
    }
    targetCtx.beginPath();
    targetCtx.moveTo(p1.x, p1.y);
    targetCtx.lineTo(p2.x, p2.y);
    targetCtx.stroke();
  }

// إضافة دالة لرسم الخطوط المكتملة على اللوحة الرئيسية عند التوقف (باستخدام السياق الصحيح)
  function drawLineFinal(p1, p2) {
    mainCtx.lineCap = 'round';
    mainCtx.lineJoin = 'round';
    mainCtx.lineWidth = brushSize;
    if (tool === 'eraser') {
      mainCtx.globalCompositeOperation = 'destination-out'; // عملية الممحاة الفعلية
      mainCtx.strokeStyle = 'rgba(0,0,0,1)';
    } else {
      mainCtx.globalCompositeOperation = 'source-over';
      mainCtx.strokeStyle = brushColor;
    }
    mainCtx.beginPath();
    mainCtx.moveTo(p1.x, p1.y);
    mainCtx.lineTo(p2.x, p2.y);
    mainCtx.stroke();
  }

  function onMove(e) {
    if (!drawing) return;
    const p = getPos(e);
    
    // 1. امسح اللوحة المؤقتة بالكامل (لإزالة الخطوة السابقة)
    tempCtx.clearRect(0, 0, tempCanvas.width, tempCanvas.height); 
    
    // 2. ارسم الخط الجديد على اللوحة المؤقتة (للمعاينة الحية)
    drawLine(last, p, tempCtx); 
    
    last = p; // للحركة التالية
    e.preventDefault();
  }

// DOM events (تم توجيه الأحداث إلى اللوحة المؤقتة للتفاعل)
  tempCanvas.addEventListener('mousedown', startDraw); // <--- تم التغيير
  tempCanvas.addEventListener('touchstart', startDraw, {passive:false}); // <--- تم التغيير
  window.addEventListener('mouseup', stopDraw);
  window.addEventListener('touchend', stopDraw, {passive:false});
  tempCanvas.addEventListener('mousemove', onMove); // <--- تم التغيير
  tempCanvas.addEventListener('touchmove', onMove, {passive:false});

  sizeInput.addEventListener('input', (e) => {
    brushSize = parseInt(e.target.value, 10);
    sizeVal.textContent = brushSize;
  });
  colorInput.addEventListener('input', (e) => brushColor = e.target.value);

  btnBrush.addEventListener('click', () => {
    tool = 'brush';
    btnBrush.classList.add('active');
    btnEraser.classList.remove('active');
  });
  btnEraser.addEventListener('click', () => {
    tool = 'eraser';
    btnEraser.classList.add('active');
    btnBrush.classList.remove('active');
  });

  btnUndo.addEventListener('click', () => doUndo());
btnClear.addEventListener('click', () => {
    pushUndo();
    // مسح اللوحة الرئيسية
    mainCtx.fillStyle = '#ffffff';
    mainCtx.fillRect(0,0,mainCanvas.width,mainCanvas.height);
    // والتأكد من مسح اللوحة المؤقتة أيضًا
    tempCtx.clearRect(0,0,tempCanvas.width,tempCanvas.height);
  });

  btnDownload.addEventListener('click', () => {
const url = mainCanvas.toDataURL('image/png');    const a = document.createElement('a');
    a.href = url;
    a.download = 'doodle.png';
    a.click();
  });
  btnBack.addEventListener('click', () => {
    if (tg) tg.close();
    else window.close();
  });


// ... (الكود قبل معالج زر الإرسال)

// معالج زر الإرسال
btnSend.addEventListener('click', () => {
    const tg = window.Telegram?.WebApp || null;
    if (!tg) {
        alert('⚠️ لم يتم اكتشاف بيئة تيليجرام.');
        return;
    }

    // ⚠️ مفتاح API الخاص بك من ImgBB
    const IMGBB_API_KEY = "adcb6daec9bef4d4e64dc34f2f8ca568"; // استبدل هنا!
    
    // 1. استخراج الصورة بجودة جيدة (لن نحتاج إلى التصغير الجذري بعد الآن!)
    // يمكنك العودة إلى أبعاد اللوحة الأصلية وجودة أعلى
    const ratio = window.devicePixelRatio || 1;
    // يمكنك تجربة PNG أو JPEG بجودة 0.8 للحصول على صورة جيدة
const dataURL = mainCanvas.toDataURL('image/jpeg', 0.8); // الجديد    
    // إعداد رسالة البوت (Base64 بدون البادئة)
    const base64Image = dataURL.replace(/^data:image\/[^;]+;base64,/, '');

    // 2. إظهار حالة التحميل للمستخدم
    tg.MainButton.setText('جاري الرفع...').show().disable();
    tg.HapticFeedback.impactOccurred('medium');

    // 3. إرسال طلب POST لرفع الصورة إلى ImgBB
    fetch(`https://api.imgbb.com/1/upload?key=${IMGBB_API_KEY}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        // Base64 يجب أن يُرسل كـ string في الفورم داتا
        body: `image=${encodeURIComponent(base64Image)}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const imageUrl = data.data.url;
            
            // 4. بعد الرفع الناجح، نرسل رابط الصورة (نص قصير) إلى البوت
            const MESSAGE_PREFIX = "DOODLE_URL::"; // ⚠️ بادئة جديدة
            const messageToSend = MESSAGE_PREFIX + imageUrl;

            if (messageToSend.length > 4000) {
                 tg.showAlert('❌ فشل: الرابط الناتج طويل جداً بشكل غير متوقع.');
                 return;
            }

            // الإرسال عبر API الـ WebApp الرسمي (سينجح لأن الرابط قصير)
            tg.sendData(messageToSend);
            
            // عند نجاح الإرسال، سيتم إغلاق الـ WebApp
            // (رسالة النجاح ستظهر للحظة قصيرة قبل الإغلاق)
            tg.showAlert('✅ تم إرسال الرابط بنجاح إلى البوت!');
            
        } else {
            tg.showAlert('❌ فشل الرفع إلى ImgBB: ' + data.error.message);
        }
    })
    .catch(error => {
        tg.showAlert('❌ خطأ في الاتصال بالخادم (ImgBB): ' + error.message);
        console.error("Fetch Error:", error);
    })
    .finally(() => {
        // إزالة حالة التحميل
        tg.MainButton.hide();
        tg.enableClosingConfirmation(); // إذا كنت تستخدمها
    });
});



  // Initialize: read init data if available
  try {
    if (tg) {
      // expand to full height
      tg.expand && tg.expand();
      const init = tg.initDataUnsafe || {};
      // If bot passed a word to draw we can display it
      // Many games pass word via fragment -> check window.location.hash as fallback
      let startWord = 'حاول التخمين';
      if (init?.query_id) {
        // nothing
      }
      // try url fragment (tgWebAppData)
      const h = decodeURIComponent(window.location.hash || '');
      const m = h.match(/tgWebAppData=([^&]+)/);
      if (m) {
        try {
          const parsed = decodeURIComponent(m[1]);
          // parsed may be like user%3D... or a more complex string; we won't rely on it now
        } catch(e){}
      }
      // optionally the bot could pass a word via query param ?word=...
      const params = new URLSearchParams(window.location.search);
      if (params.has('word')) startWord = params.get('word');
      wordBox.textContent = startWord;
    }
  } catch(e){
    console.warn('init error', e);
  }

})();
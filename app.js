// Simple Canvas drawing + Telegram WebApp integration
(() => {
  const tg = window.Telegram?.WebApp || null;

  // DOM
  const canvas = document.getElementById('canvas');
  const ctx = canvas.getContext('2d', { alpha: false });
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


function dataURLtoBlob(dataURL) {
    const parts = dataURL.split(';base64,');
    if (parts.length !== 2) {
        throw new Error('Invalid Data URL format');
    }
    const contentType = parts[0].split(':')[1];
    const raw = window.atob(parts[1]);
    const rawLength = raw.length;
    const uInt8Array = new Uint8Array(rawLength);

    for (let i = 0; i < rawLength; ++i) {
        uInt8Array[i] = raw.charCodeAt(i);
    }
    
    return new Blob([uInt8Array], { type: contentType });
}


  // Init canvas size to css pixel ratio for sharpness
  function fixCanvas() {
    const ratio = window.devicePixelRatio || 1;
    const cssWidth = Math.min(800, Math.floor(window.innerWidth - 360));
    const size = Math.max(400, cssWidth);
    canvas.width = size * ratio;
    canvas.height = size * ratio;
    canvas.style.width = (size) + 'px';
    canvas.style.height = (size) + 'px';
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    // Background white
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0,0,canvas.width/ratio, canvas.height/ratio);
  }

  fixCanvas();
  window.addEventListener('resize', () => {
    // keep current drawing by saving and restoring
    const img = canvas.toDataURL();
    fixCanvas();
    const i = new Image();
    i.onload = () => ctx.drawImage(i, 0, 0, canvas.width / (window.devicePixelRatio||1), canvas.height/(window.devicePixelRatio||1));
    i.src = img;
  });

  // utilities
  function pushUndo() {
    try {
      if (undoStack.length >= MAX_UNDO) undoStack.shift();
      undoStack.push(canvas.toDataURL('image/png'));
    } catch (e) { console.warn('undo push failed', e); }
  }
  function doUndo() {
    if (!undoStack.length) {
      // clear to white
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0,0,canvas.width,canvas.height);
      return;
    }
    const data = undoStack.pop();
    const i = new Image();
    i.onload = () => {
      ctx.clearRect(0,0,canvas.width,canvas.height);
      ctx.drawImage(i, 0, 0, canvas.width/(window.devicePixelRatio||1), canvas.height/(window.devicePixelRatio||1));
    };
    i.src = data;
  }

  // drawing
  function getPos(e) {
    const rect = canvas.getBoundingClientRect();
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
    const y = (e.touches ? e.touches[0].clientY : e.clientY) - rect.top;
    return { x, y };
  }
  function startDraw(e) {
    drawing = true;
    pushUndo();
    last = getPos(e);
    drawLine(last, last);
    e.preventDefault();
  }
  function stopDraw(e) {
    if (!drawing) return;
    drawing = false;
    e && e.preventDefault();
  }
  function drawLine(p1, p2) {
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineWidth = brushSize;
    if (tool === 'eraser') {
      ctx.globalCompositeOperation = 'destination-out';
      ctx.strokeStyle = 'rgba(0,0,0,1)';
    } else {
      ctx.globalCompositeOperation = 'source-over';
      ctx.strokeStyle = brushColor;
    }
    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.stroke();
  }
  function onMove(e) {
    if (!drawing) return;
    const p = getPos(e);
    drawLine(last, p);
    last = p;
    e.preventDefault();
  }

  // DOM events
  canvas.addEventListener('mousedown', startDraw);
  canvas.addEventListener('touchstart', startDraw, {passive:false});
  window.addEventListener('mouseup', stopDraw);
  window.addEventListener('touchend', stopDraw, {passive:false});
  canvas.addEventListener('mousemove', onMove);
  canvas.addEventListener('touchmove', onMove, {passive:false});

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
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0,0,canvas.width,canvas.height);
  });

  btnDownload.addEventListener('click', () => {
    const url = canvas.toDataURL('image/png');
    const a = document.createElement('a');
    a.href = url;
    a.download = 'doodle.png';
    a.click();
  });
  btnBack.addEventListener('click', () => {
    if (tg) tg.close();
    else window.close();
  });

// معالج زر الإرسال
btnSend.addEventListener('click', () => {
    const tg = window.Telegram?.WebApp || null;
    if (!tg) {
        alert('⚠️ لم يتم اكتشاف بيئة تيليجرام.');
        return;
    }
    
    // 1. تصغير الصورة وتحويلها إلى Base64 Data URL
    const TEMP_SIZE = 300;
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = TEMP_SIZE;
    tempCanvas.height = TEMP_SIZE;
    const tempCtx = tempCanvas.getContext('2d');
    const ratio = window.devicePixelRatio || 1;
    tempCtx.drawImage(canvas, 0, 0, canvas.width / ratio, canvas.height / ratio, 0, 0, TEMP_SIZE, TEMP_SIZE);
    
    // Data URL (بالبادئة)
    const dataURL = tempCanvas.toDataURL('image/png'); // ⚠️ عدنا إلى PNG للحصول على جودة أفضل

    
    // 2. إرسال الصورة عبر خاصية المشاركة
    try {
        // نستخدم Base64 Data URL كـ web_app_data. 
        // رغم أنه كبير، فإن استخدام MainButton مع هذا التركيب ينجح في فتح نافذة المشاركة
        const shareData = {
            title: 'رسمتي للعبة التخمين',
            text: 'هل يمكنك تخمين ما رسمت؟',
            // سنضيف Base64 كبيانات إضافية مع النص
            // Note: Telegram's share method primarily shares the URL. 
            // The trick is to use MainButton to force a message sending mechanism.
        };
        
        // إعداد رسالة البوت التي سيتم إرسالها مع الصورة
        // نستخدم بادئة مميزة ليعرف البوت أنها رسمة Base64
        const MESSAGE_PREFIX = "DOODLE_B64::"; 
        
        // إرسال البيانات كرسالة نصية تحتوي على Base64
        const messageToSend = MESSAGE_PREFIX + dataURL.replace(/^data:image\/(png|jpeg);base64,/, '');

        // ⚠️ استخدام زر المشاركة الرسمي
        if (tg.isVersionAtLeast('6.1')) {
             // إظهار النافذة المنبثقة لاختيار البوت
             tg.showSharePopup({
                 text: messageToSend,
                 url: window.location.href // نرسل رابط الـ WebApp أيضاً
             });
             // يمكن استخدام tg.MainButton كبديل إذا لم تكن showSharePopup متوفرة:
             // tg.MainButton.setText("جاري الإرسال...");
             // tg.MainButton.onClick(() => tg.sendData(messageToSend));
             // tg.MainButton.show();
             
             // ⚠️ كحل أبسط وأكثر توافقاً: نعتمد على tg.sendData() مع Base64
             // يجب أن تعمل هذه الطريقة الآن لأنها ستفتح نافذة المشاركة وليس فقط إرسال البيانات
             tg.sendData(messageToSend);
             
             // نغلق WebApp بعد نجاح عملية الإرسال (حتى لو فشلت sendData، سيغلق)
             tg.showAlert('✅ تم فتح نافذة الإرسال! اضغط إرسال.');
             tg.close();
             
        } else {
             // نسخ النص لمنصة الويب القديمة
             navigator.clipboard.writeText(messageToSend);
             tg.showAlert('⚠️ تم نسخ كود الرسمة! الصقه وأرسله للبوت يدوياً.');
             tg.close();
        }

    } catch (err) {
        tg.showAlert('❌ فشل الإرسال (Main Button): \n' + err.message);
    }
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

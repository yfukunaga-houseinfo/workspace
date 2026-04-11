// ==============================================
// スイカゲーム - Watermelon Game
// ==============================================

(function () {
    'use strict';

    // --- Matter.js モジュール ---
    const { Engine, Render, Runner, Bodies, Body, Composite, Events, Vector } = Matter;

    // --- ゲーム設定 ---
    const WALL_THICKNESS = 20;
    const DROP_ZONE_Y = 80;        // フルーツ落下ライン
    const GAME_OVER_LINE_Y = 100;  // ゲームオーバーライン
    const DROP_COOLDOWN = 500;     // 落下後のクールダウン（ms）
    const GAME_OVER_GRACE = 2000;  // ゲームオーバー判定の猶予時間（ms）

    // --- フルーツ定義（小さい順） ---
    const FRUITS = [
        { name: 'さくらんぼ', radius: 15, color: '#e74c3c', emoji: '🍒', score: 1 },
        { name: 'いちご',     radius: 20, color: '#ff6b81', emoji: '🍓', score: 3 },
        { name: 'ぶどう',     radius: 26, color: '#8e44ad', emoji: '🍇', score: 6 },
        { name: 'デコポン',   radius: 32, color: '#f39c12', emoji: '🍊', score: 10 },
        { name: 'かき',       radius: 38, color: '#e67e22', emoji: '🍑', score: 15 },
        { name: 'りんご',     radius: 44, color: '#c0392b', emoji: '🍎', score: 21 },
        { name: 'なし',       radius: 50, color: '#f1c40f', emoji: '🍐', score: 28 },
        { name: 'もも',       radius: 56, color: '#ffb6c1', emoji: '🍑', score: 36 },
        { name: 'パイナップル', radius: 62, color: '#f9ca24', emoji: '🍍', score: 45 },
        { name: 'メロン',     radius: 68, color: '#2ecc71', emoji: '🍈', score: 55 },
        { name: 'スイカ',     radius: 75, color: '#27ae60', emoji: '🍉', score: 66 },
    ];

    // ランダムに落とすフルーツの最大インデックス（最初の5種類）
    const MAX_DROP_INDEX = 4;

    // --- キャンバスサイズ計算 ---
    function getCanvasSize() {
        const maxWidth = Math.min(window.innerWidth, 400);
        const gameWidth = maxWidth;
        const gameHeight = Math.min(window.innerHeight - 90, 600);
        return { width: gameWidth, height: gameHeight };
    }

    // --- ゲーム状態 ---
    let engine, runner, canvas, ctx, nextCanvas, nextCtx;
    let gameWidth, gameHeight;
    let score = 0;
    let currentFruitIndex = 0;
    let nextFruitIndex = 0;
    let dropX = 0;
    let canDrop = true;
    let isGameOver = false;
    let fruitBodies = [];         // ゲーム内のフルーツボディ一覧
    let merging = new Set();      // マージ中のボディID
    let gameOverTimers = {};      // ゲームオーバーライン超過タイマー
    let guideLine = true;         // ガイドライン表示

    // --- 初期化 ---
    function init() {
        const size = getCanvasSize();
        gameWidth = size.width;
        gameHeight = size.height;

        canvas = document.getElementById('game-canvas');
        ctx = canvas.getContext('2d');
        canvas.width = gameWidth;
        canvas.height = gameHeight;

        nextCanvas = document.getElementById('next-canvas');
        nextCtx = nextCanvas.getContext('2d');

        // Matter.js エンジン作成
        engine = Engine.create({
            gravity: { x: 0, y: 1.8 }
        });

        // 壁と床を作成
        const walls = [
            // 床
            Bodies.rectangle(gameWidth / 2, gameHeight + WALL_THICKNESS / 2, gameWidth + WALL_THICKNESS * 2, WALL_THICKNESS, {
                isStatic: true, label: 'floor',
                render: { fillStyle: '#ff6b35' }
            }),
            // 左壁
            Bodies.rectangle(-WALL_THICKNESS / 2, gameHeight / 2, WALL_THICKNESS, gameHeight * 2, {
                isStatic: true, label: 'wall',
                render: { fillStyle: '#ff6b35' }
            }),
            // 右壁
            Bodies.rectangle(gameWidth + WALL_THICKNESS / 2, gameHeight / 2, WALL_THICKNESS, gameHeight * 2, {
                isStatic: true, label: 'wall',
                render: { fillStyle: '#ff6b35' }
            }),
        ];
        Composite.add(engine.world, walls);

        // 初期フルーツ
        currentFruitIndex = randomFruitIndex();
        nextFruitIndex = randomFruitIndex();
        dropX = gameWidth / 2;

        // 衝突イベント
        Events.on(engine, 'collisionStart', handleCollision);

        // 入力イベント
        canvas.addEventListener('touchstart', onTouchStart, { passive: false });
        canvas.addEventListener('touchmove', onTouchMove, { passive: false });
        canvas.addEventListener('touchend', onTouchEnd, { passive: false });
        canvas.addEventListener('mousedown', onMouseDown);
        canvas.addEventListener('mousemove', onMouseMove);
        canvas.addEventListener('mouseup', onMouseUp);

        // リスタート
        document.getElementById('restart-btn').addEventListener('click', restart);

        // ゲームループ開始
        runner = Runner.create();
        Runner.run(runner, engine);
        requestAnimationFrame(gameLoop);

        drawNextFruit();
        updateScoreDisplay();
    }

    // --- ランダムフルーツインデックス ---
    function randomFruitIndex() {
        return Math.floor(Math.random() * (MAX_DROP_INDEX + 1));
    }

    // --- フルーツ落下 ---
    function dropFruit() {
        if (!canDrop || isGameOver) return;

        const fruit = FRUITS[currentFruitIndex];
        const x = Math.max(fruit.radius + 3, Math.min(gameWidth - fruit.radius - 3, dropX));
        const body = Bodies.circle(x, DROP_ZONE_Y, fruit.radius, {
            restitution: 0.2,
            friction: 0.5,
            density: 0.002,
            label: 'fruit',
            fruitIndex: currentFruitIndex,
        });

        Composite.add(engine.world, body);
        fruitBodies.push(body);

        // 次のフルーツへ
        currentFruitIndex = nextFruitIndex;
        nextFruitIndex = randomFruitIndex();
        drawNextFruit();

        // クールダウン
        canDrop = false;
        setTimeout(() => { canDrop = true; }, DROP_COOLDOWN);
    }

    // --- 衝突処理（マージ） ---
    function handleCollision(event) {
        const pairs = event.pairs;

        for (const pair of pairs) {
            const bodyA = pair.bodyA;
            const bodyB = pair.bodyB;

            // 両方ともフルーツか確認
            if (bodyA.label !== 'fruit' || bodyB.label !== 'fruit') continue;
            // 同じフルーツインデックスか
            if (bodyA.fruitIndex !== bodyB.fruitIndex) continue;
            // 既にマージ中でないか
            if (merging.has(bodyA.id) || merging.has(bodyB.id)) continue;
            // スイカ同士はマージしない（最大サイズ）
            if (bodyA.fruitIndex >= FRUITS.length - 1) continue;

            // マージ実行
            merging.add(bodyA.id);
            merging.add(bodyB.id);

            const newIndex = bodyA.fruitIndex + 1;
            const newFruit = FRUITS[newIndex];
            const midX = (bodyA.position.x + bodyB.position.x) / 2;
            const midY = (bodyA.position.y + bodyB.position.y) / 2;

            // 古いボディを削除
            Composite.remove(engine.world, bodyA);
            Composite.remove(engine.world, bodyB);
            fruitBodies = fruitBodies.filter(b => b.id !== bodyA.id && b.id !== bodyB.id);
            merging.delete(bodyA.id);
            merging.delete(bodyB.id);

            // 新しいフルーツを作成
            const newBody = Bodies.circle(midX, midY, newFruit.radius, {
                restitution: 0.2,
                friction: 0.5,
                density: 0.002,
                label: 'fruit',
                fruitIndex: newIndex,
            });
            // 少し上向きの力を加えて演出
            Body.setVelocity(newBody, { x: 0, y: -2 });
            Composite.add(engine.world, newBody);
            fruitBodies.push(newBody);

            // スコア加算
            score += newFruit.score;
            updateScoreDisplay();

            // マージエフェクト
            spawnMergeEffect(midX, midY, newFruit);
        }
    }

    // --- マージエフェクト ---
    let mergeEffects = [];

    function spawnMergeEffect(x, y, fruit) {
        const particles = [];
        for (let i = 0; i < 8; i++) {
            const angle = (Math.PI * 2 / 8) * i;
            particles.push({
                x: x,
                y: y,
                vx: Math.cos(angle) * 3,
                vy: Math.sin(angle) * 3,
                life: 1.0,
                color: fruit.color,
                radius: 4,
            });
        }
        mergeEffects.push(...particles);
    }

    function updateMergeEffects() {
        for (let i = mergeEffects.length - 1; i >= 0; i--) {
            const p = mergeEffects[i];
            p.x += p.vx;
            p.y += p.vy;
            p.life -= 0.04;
            p.radius *= 0.96;
            if (p.life <= 0) {
                mergeEffects.splice(i, 1);
            }
        }
    }

    function drawMergeEffects() {
        for (const p of mergeEffects) {
            ctx.globalAlpha = p.life;
            ctx.fillStyle = p.color;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.globalAlpha = 1;
    }

    // --- ゲームオーバー判定 ---
    function checkGameOver() {
        if (isGameOver) return;

        const now = Date.now();
        const activeFruitIds = new Set(fruitBodies.map(b => b.id));

        // 不要なタイマーを削除
        for (const id of Object.keys(gameOverTimers)) {
            if (!activeFruitIds.has(Number(id))) {
                delete gameOverTimers[id];
            }
        }

        for (const body of fruitBodies) {
            // 速度がほぼゼロ（安定している）かつゲームオーバーラインを超えている
            const speed = Vector.magnitude(body.velocity);
            if (body.position.y - body.circleRadius < GAME_OVER_LINE_Y && speed < 1.0) {
                if (!gameOverTimers[body.id]) {
                    gameOverTimers[body.id] = now;
                } else if (now - gameOverTimers[body.id] > GAME_OVER_GRACE) {
                    triggerGameOver();
                    return;
                }
            } else {
                delete gameOverTimers[body.id];
            }
        }
    }

    function triggerGameOver() {
        isGameOver = true;
        canDrop = false;
        document.getElementById('final-score').textContent = score;
        document.getElementById('game-over-overlay').classList.remove('hidden');
    }

    // --- リスタート ---
    function restart() {
        // ワールドをクリア
        Composite.clear(engine.world, false);

        // 壁を再設置
        const walls = [
            Bodies.rectangle(gameWidth / 2, gameHeight + WALL_THICKNESS / 2, gameWidth + WALL_THICKNESS * 2, WALL_THICKNESS, {
                isStatic: true, label: 'floor'
            }),
            Bodies.rectangle(-WALL_THICKNESS / 2, gameHeight / 2, WALL_THICKNESS, gameHeight * 2, {
                isStatic: true, label: 'wall'
            }),
            Bodies.rectangle(gameWidth + WALL_THICKNESS / 2, gameHeight / 2, WALL_THICKNESS, gameHeight * 2, {
                isStatic: true, label: 'wall'
            }),
        ];
        Composite.add(engine.world, walls);

        // 状態リセット
        fruitBodies = [];
        mergeEffects = [];
        merging.clear();
        gameOverTimers = {};
        score = 0;
        isGameOver = false;
        canDrop = true;
        currentFruitIndex = randomFruitIndex();
        nextFruitIndex = randomFruitIndex();
        dropX = gameWidth / 2;

        updateScoreDisplay();
        drawNextFruit();
        document.getElementById('game-over-overlay').classList.add('hidden');
    }

    // --- 入力処理 ---
    let isDragging = false;

    function getCanvasX(clientX) {
        const rect = canvas.getBoundingClientRect();
        return clientX - rect.left;
    }

    function onTouchStart(e) {
        e.preventDefault();
        isDragging = true;
        const touch = e.touches[0];
        dropX = getCanvasX(touch.clientX);
    }

    function onTouchMove(e) {
        e.preventDefault();
        if (!isDragging) return;
        const touch = e.touches[0];
        dropX = getCanvasX(touch.clientX);
    }

    function onTouchEnd(e) {
        e.preventDefault();
        if (isDragging) {
            dropFruit();
            isDragging = false;
        }
    }

    function onMouseDown(e) {
        isDragging = true;
        dropX = getCanvasX(e.clientX);
    }

    function onMouseMove(e) {
        if (!isDragging) {
            dropX = getCanvasX(e.clientX);
            return;
        }
        dropX = getCanvasX(e.clientX);
    }

    function onMouseUp(e) {
        if (isDragging) {
            dropFruit();
            isDragging = false;
        }
    }

    // --- 描画 ---
    function drawFruit(x, y, fruitIndex, alpha) {
        const fruit = FRUITS[fruitIndex];
        const r = fruit.radius;

        ctx.save();
        ctx.globalAlpha = alpha || 1;

        // 影
        ctx.shadowColor = 'rgba(0,0,0,0.3)';
        ctx.shadowBlur = 8;
        ctx.shadowOffsetY = 3;

        // グラデーション
        const gradient = ctx.createRadialGradient(x - r * 0.3, y - r * 0.3, r * 0.1, x, y, r);
        gradient.addColorStop(0, lightenColor(fruit.color, 40));
        gradient.addColorStop(0.7, fruit.color);
        gradient.addColorStop(1, darkenColor(fruit.color, 30));

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();

        // ハイライト
        ctx.shadowColor = 'transparent';
        const hlGradient = ctx.createRadialGradient(x - r * 0.3, y - r * 0.4, r * 0.05, x - r * 0.3, y - r * 0.4, r * 0.5);
        hlGradient.addColorStop(0, 'rgba(255,255,255,0.5)');
        hlGradient.addColorStop(1, 'rgba(255,255,255,0)');
        ctx.fillStyle = hlGradient;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();

        // 絵文字
        const fontSize = Math.max(r * 0.8, 12);
        ctx.font = `${fontSize}px serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(fruit.emoji, x, y + 1);

        ctx.restore();
    }

    function drawGuideAndPreview() {
        if (isGameOver || !canDrop) return;

        const fruit = FRUITS[currentFruitIndex];
        const x = Math.max(fruit.radius + 3, Math.min(gameWidth - fruit.radius - 3, dropX));

        // ガイドライン（点線）
        ctx.setLineDash([5, 5]);
        ctx.strokeStyle = 'rgba(255, 107, 53, 0.3)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, DROP_ZONE_Y + fruit.radius);
        ctx.lineTo(x, gameHeight);
        ctx.stroke();
        ctx.setLineDash([]);

        // プレビューフルーツ
        drawFruit(x, DROP_ZONE_Y, currentFruitIndex, 0.7);
    }

    function drawGameOverLine() {
        ctx.strokeStyle = 'rgba(255, 0, 0, 0.3)';
        ctx.lineWidth = 1;
        ctx.setLineDash([10, 5]);
        ctx.beginPath();
        ctx.moveTo(0, GAME_OVER_LINE_Y);
        ctx.lineTo(gameWidth, GAME_OVER_LINE_Y);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    function drawWalls() {
        ctx.fillStyle = '#ff6b35';
        // 床
        ctx.fillRect(0, gameHeight - 2, gameWidth, 2);
    }

    function drawNextFruit() {
        nextCtx.clearRect(0, 0, 60, 60);
        const fruit = FRUITS[nextFruitIndex];
        const scale = Math.min(25 / fruit.radius, 1);
        const r = fruit.radius * scale;

        // グラデーション
        const gradient = nextCtx.createRadialGradient(30 - r * 0.3, 30 - r * 0.3, r * 0.1, 30, 30, r);
        gradient.addColorStop(0, lightenColor(fruit.color, 40));
        gradient.addColorStop(0.7, fruit.color);
        gradient.addColorStop(1, darkenColor(fruit.color, 30));

        nextCtx.fillStyle = gradient;
        nextCtx.beginPath();
        nextCtx.arc(30, 30, r, 0, Math.PI * 2);
        nextCtx.fill();

        const fontSize = Math.max(r * 0.8, 10);
        nextCtx.font = `${fontSize}px serif`;
        nextCtx.textAlign = 'center';
        nextCtx.textBaseline = 'middle';
        nextCtx.fillText(fruit.emoji, 30, 31);
    }

    // --- メインゲームループ ---
    function gameLoop() {
        // キャンバスクリア
        ctx.clearRect(0, 0, gameWidth, gameHeight);

        // 背景グラデーション
        const bgGrad = ctx.createLinearGradient(0, 0, 0, gameHeight);
        bgGrad.addColorStop(0, '#2d1b69');
        bgGrad.addColorStop(1, '#1a0a2e');
        ctx.fillStyle = bgGrad;
        ctx.fillRect(0, 0, gameWidth, gameHeight);

        // 壁・床
        drawWalls();

        // ゲームオーバーライン
        drawGameOverLine();

        // フルーツ描画
        for (const body of fruitBodies) {
            if (body.label === 'fruit') {
                drawFruit(body.position.x, body.position.y, body.fruitIndex, 1);
            }
        }

        // マージエフェクト
        updateMergeEffects();
        drawMergeEffects();

        // ガイド・プレビュー
        drawGuideAndPreview();

        // ゲームオーバー判定
        checkGameOver();

        requestAnimationFrame(gameLoop);
    }

    // --- スコア表示更新 ---
    function updateScoreDisplay() {
        document.getElementById('score').textContent = score;
    }

    // --- ユーティリティ: 色変換 ---
    function lightenColor(hex, percent) {
        const num = parseInt(hex.replace('#', ''), 16);
        const r = Math.min(255, (num >> 16) + Math.round(255 * percent / 100));
        const g = Math.min(255, ((num >> 8) & 0x00FF) + Math.round(255 * percent / 100));
        const b = Math.min(255, (num & 0x0000FF) + Math.round(255 * percent / 100));
        return `rgb(${r},${g},${b})`;
    }

    function darkenColor(hex, percent) {
        const num = parseInt(hex.replace('#', ''), 16);
        const r = Math.max(0, (num >> 16) - Math.round(255 * percent / 100));
        const g = Math.max(0, ((num >> 8) & 0x00FF) - Math.round(255 * percent / 100));
        const b = Math.max(0, (num & 0x0000FF) - Math.round(255 * percent / 100));
        return `rgb(${r},${g},${b})`;
    }

    // --- 開始 ---
    window.addEventListener('load', init);
})();

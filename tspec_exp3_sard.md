
# T-Spec: Обновление 1.7 (Визуальный индикатор загрузки / Spinner)

## 1. Общие сведения
* **Затрагиваемые модули:** Frontend (`style.css`, `app.js`). Backend не требует изменений.
* **Цель:** Улучшить UX (пользовательский опыт) при длительном ожидании ответа от тяжелых моделей (gemini-3.1-pro), заменив статичный текст на анимированный индикатор загрузки.

## 2. Архитектурные ограничения
* ❌ **ЗАПРЕЩЕНО:** Использовать тяжелые GIF-анимации, сторонние библиотеки (FontAwesome) или SVG-файлы, требующие отдельных HTTP-запросов.
* ✅ **ТРЕБОВАНИЕ:** Спиннер должен быть реализован исключительно средствами чистого CSS (анимация `border` или `transform: rotate`).

## 3. Требования к реализации

**FR-UI4: CSS Спиннер (style.css)**
Необходимо добавить стили для нового элемента `.spinner` и анимацию вращения в конец файла `style.css`. Спиннер должен органично вписываться в темную тему (использовать переменные `--primary` или `--text-color`).

*Пример реализации для `style.css`:*
```css
.spinner-container {
    display: flex;
    align-items: center;
    gap: 10px;
}

.spinner {
    width: 20px;
    height: 20px;
    border: 3px solid rgba(88, 166, 255, 0.2); /* Полупрозрачный цвет основы */
    border-top: 3px solid var(--primary); /* Яркий цвет бегунка */
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

```

**FR-JS6: Интеграция спиннера в DOM (app.js)**
Текущий код в функции `sendMessage(stateId)` создает индикатор ожидания как простой текст. Необходимо заменить установку `innerText` на `innerHTML` с добавлением верстки спиннера.

*Было в `app.js` (Оптимистичный UI для ИИ):*

```javascript
    const mMsg = document.createElement('div');
    mMsg.className = 'message model';
    mMsg.id = 'thinking-indicator';
    mMsg.innerText = getTrans('msg_thinking');
    chatBox.appendChild(mMsg);

```

*Должно стать:*

```javascript
    const mMsg = document.createElement('div');
    mMsg.className = 'message model';
    mMsg.id = 'thinking-indicator';
    // Добавляем HTML-структуру спиннера и текста
    mMsg.innerHTML = `
        <div class="spinner-container">
            <div class="spinner"></div>
            <span>${getTrans('msg_thinking')}</span>
        </div>
    `;
    chatBox.appendChild(mMsg);

```

## 4. План интеграции (Checklist)

1. [ ] Внести классы `.spinner-container`, `.spinner` и `@keyframes spin` в `style.css`.
2. [ ] Найти функцию `sendMessage` в `app.js` и заменить строку `mMsg.innerText = ...` на `mMsg.innerHTML = ...` с разметкой спиннера.
3. [ ] Проверить, что спиннер исчезает вместе с текстом (так как код `chatBox.removeChild(...)` удаляет весь блок `#thinking-indicator` целиком при ответе API).


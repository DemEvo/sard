
# T-Spec: Обновление 1.8 (Рестайлинг кнопок и скроллбаров / Restyling)

## 1. Общие сведения (Front Matter)

* **Название проекта:** AI T-Spec Generator (SARD)
* **Версия спецификации:** 1.8 (Aesthetic Improvement Sprint)
* **Затрагиваемые модули:** Frontend (`style.css`, minor `index.html` adjustment). Backend и JS логика остаются без изменений.
* **Цель:** Привести нативные UI-элементы (кнопка выбора файла и полоса прокрутки) в соответствие с общей темной эстетикой SARD. Сделать полосы прокрутки тонкими, а кнопки — кастомными.

## 2. Архитектурные ограничения (Constraints)

* ❌ **ЗАПРЕЩЕНО:** Использование сторонних CSS-библиотек (Bootstrap, Tailwind). Только чистый Vanilla CSS.
* ✅ **ТРЕБОВАНИЕ:** Стилизация полос прокрутки должна работать во всех современных браузерах (использование `-webkit-scrollbar` для Chrome/Safari/Edge и стандартного `scrollbar-width` для Firefox).

## 3. Требования к рестайлингу интерфейса (Restyling Specs)

**FR-RESTYLE1: Нативная кнопка выбора файла (Custom File Input)**
* **Проблема:** Стандартный элемент `<input type="file">` имеет встроенный стиль браузера, который не поддается прямому изменению CSS и выбивается из темы SARD.
* **Решение:** Использовать метод скрытия нативного ввода и стилизации его `<label>`.

*Пошаговая реализация:*
1.  **index.html**: Внутри `#files-list` найти `<input type="file" ...>`. Обернуть его в `div.file-input-wrapper` и добавить `<label for="...">Выберите файл</label>`.
```html
<div class="file-input-wrapper">
    <input type="file" id="file-input" style="opacity: 0; position: absolute; z-index: -1;">
    <label for="file-input" class="custom-file-upload">
        📁 <span data-i18n="btn_choose_file">Выберите файл</span>
    </label>
</div>

```

2. **style.css**: Стилизовать `.custom-file-upload`. Он должен выглядеть как кнопка SARD: темный фон, светлая рамка, hover-эффект.

```css
.file-input-wrapper { display: flex; align-items: center; gap: 10px; }
.custom-file-upload {
    display: inline-block;
    padding: 8px 16px;
    background-color: var(--card-bg); /* Использовать переменную темного фона */
    border: 1px solid var(--border-color); /* Использовать переменную рамки */
    border-radius: 6px;
    color: var(--text-color);
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s;
}
.custom-file-upload:hover {
    border-color: var(--primary); /* Использовать цвет акцента (синий) */
    background-color: rgba(88, 166, 255, 0.1);
}

```

**FR-RESTYLE2: Полоса прокрутки (Thinner & Polished Scrollbar)**

* **Проблема:** Стандартная полоса прокрутки в темной теме выглядит слишком толстой и грубой.
* **Решение:** Глобально переопределить стили для всех элементов с `overflow: auto/scroll`.

*Пример реализации для `style.css`:*

```css
/* --- Скроллбары SARD --- */

/* Глобальный скроллбар (body и блоки) */
::-webkit-scrollbar {
    width: 6px; /* Более тонкая полоса (ползунок) */
    height: 6px; /* Для горизонтального скролла */
}

/* Ползунок (сам скролл) */
::-webkit-scrollbar-thumb {
    background-color: rgba(255, 255, 255, 0.1); /* Полупрозрачный светлый */
    border-radius: 10px;
    transition: background-color 0.2s;
}

/* Эффект наведения на ползунок */
::-webkit-scrollbar-thumb:hover {
    background-color: var(--primary); /* Синий цвет акцента SARD при наведении */
}

/* Трек (дорожка) */
::-webkit-scrollbar-track {
    background: transparent; /* Полностью прозрачный трек */
}

/* Firefox поддержка (стандартная) */
* {
    scrollbar-width: thin; /* Более тонкий */
    scrollbar-color: rgba(255, 255, 255, 0.1) transparent; /* Ползунок, Трек */
}

```

## 4. План интеграции (Checklist)

1. [ ] **index.html**: Применить разметку из FR-RESTYLE1 к `#files-list`.
2. [ ] **app.js**: Убедиться, что `renderFilesList()` (FR-11) использует новый синтаксис `div.file-input-wrapper` при перерисовке. (Тут потребуется маленькая правка в JS, чтобы перерисовка файла не ломала пользовательский ввод).
3. [ ] **style.css**: Внести CSS классы из FR-RESTYLE1 и FR-RESTYLE2 в `style.css`. Убедиться в использовании существующих CSS переменных для цветов тем.


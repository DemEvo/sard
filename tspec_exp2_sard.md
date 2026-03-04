
# T-Spec: Обновление 1.6 (Многопроектность и навигация)

## 1. Общие сведения (Front Matter)

* **Название проекта:** AI T-Spec Generator (SARD)
* **Версия спецификации:** 1.6 (Project Management Sprint)
* **Затрагиваемые модули:** Frontend (`app.js`, `index.html`, `style.css`). Backend не требует изменений.
* **Цель:** Заменить статичную заглушку MVP на полноценный селектор проектов с возможностью создания новых сессий (проектов) и переключения между ними "на лету".

## 2. Архитектурные ограничения (Constraints)

* ❌ **ЗАПРЕЩЕНО:** Использование сторонних библиотек UI-компонентов (Select2, Selectize и т.д.). Используем только нативные HTML-элементы `<select>` и `<button>`.
* ❌ **ЗАПРЕЩЕНО:** Вносить изменения в схему БД или роуты Flask (бэкенд уже поддерживает нужный функционал).
* ✅ **РАЗРЕШЕНО:** Использование стандартного браузерного `prompt()` для запроса названия нового проекта ради экономии времени на разработку модальных окон.

## 3. Требования к интерфейсу (UI/UX)

**FR-UI1: Панель выбора проекта (Project Selector)**

* **Проблема:** В `index.html` контейнер `#project-selector` выводит статичный текст. Нет механизма создания новых сессий.
* **Решение:** Внутри блока `<header>` контейнер `#project-selector` должен динамически рендерить два элемента:
  1. Выпадающий список `<select>` со списком всех существующих проектов.
  2. Кнопку `+ <span data-i18n="btn_new_project">Новый проект</span>` для создания проекта.
* **Поведение:** Элементы должны быть выстроены в строку (Flexbox, `gap: 10px`, `align-items: center`).

## 4. Требования к Фронтенду (Логика Vanilla JS)

**FR-JS1: Обновление словаря локализации (L10n)**

В объект `translations` необходимо добавить новые ключи:
* **ru:** `btn_new_project: "Новый проект"`, `prompt_project_name: "Введите название нового проекта:"`, `default_project_name: "Новый проект"`
* **en:** `btn_new_project: "New Project"`, `prompt_project_name: "Enter new project name:"`, `default_project_name: "New Project"`

**FR-JS2: Состояние списка проектов**

В `app.js` добавить глобальную переменную `let allProjects = [];`.
Обновить функцию `bootstrap()`, чтобы она сохраняла массив проектов:
```javascript
async function bootstrap() {
    updateTranslations();
    const res = await fetch('/api/projects');
    allProjects = await res.json(); // Сохраняем в глобальную переменную

    if (allProjects.length > 0) {
        // Берем последний открытый или созданный проект (или по умолчанию первый)
        await loadProject(allProjects[allProjects.length - 1].id);
    } else {
        await createNewProject(getTrans('new_project'));
    }
}

```

**FR-JS3: Динамический рендеринг селектора**

Функция `renderProjectSelector()` должна перестраивать DOM:

* Создавать `<select onchange="switchProject(this.value)">`.
* Проходиться циклом по `allProjects` и добавлять `<option value="id">Название</option>`.
* Устанавливать `selected` для текущего `projectState.project.id`.
* Добавлять кнопку создания рядом с селектором.

**FR-JS4: Функция переключения (`switchProject`)**

Создать функцию:

```javascript
async function switchProject(projectId) {
    if (projectId == currentProjectId) return;
    await loadProject(projectId);
}

```

**FR-JS5: Функция создания с запросом имени (`promptNewProject`)**

Добавить функцию, которая вызывается по кнопке "Новый проект":

```javascript
async function promptNewProject() {
    let title = prompt(getTrans('prompt_project_name'), getTrans('default_project_name'));
    if (!title || title.trim() === "") return; // Отмена, если пусто

    const res = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title.trim() })
    });
    const newProj = await res.json();
    
    // Обновляем список проектов и загружаем новый
    const listRes = await fetch('/api/projects');
    allProjects = await listRes.json();
    await loadProject(newProj.id);
}

```

## 5. План интеграции (Checklist)

Разработчику необходимо выполнить:

1. [ ] **app.js**: Добавить переводы в `translations`.
2. [ ] **app.js**: Добавить `let allProjects = []` и обновить `bootstrap()`.
3. [ ] **app.js**: Полностью переписать `renderProjectSelector()`, чтобы он генерировал `<select>` и кнопку.
4. [ ] **app.js**: Реализовать функции `switchProject(id)` и `promptNewProject()`.
5. [ ] **style.css**: Стилизовать новый `<select>` (фон, бордеры, цвет текста под темную тему), чтобы он не выбивался из дизайна.


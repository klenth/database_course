"use strict";

function $(sel) {
    return document.querySelector(sel);
}

function $$(sel) {
    return document.querySelectorAll(sel);
}

/* Stolen from Django docs */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/*
 * Initiates an asynchronous Ajax request. If a CSRF token is found, it will be passed in the X-CSRFToken request
 * header.
 *
 * The following parameters are recognized:
 * - url (required)
 * - method (required): GET or POST
 * - body (optional): the data to send
 * - contentType (optional): the content type of the body, e.g. application/json or multipart/form-data
 * - timeout (optional): length of time to wait (in milliseconds) before declaring a timeout. Default: 5000
 * - onSuccess (optional): a function that will be called if and when the request is successfully completed. A single
 *       parameter of the returned data is given.
 * - onTimeout (optional): a function that will be called if and when the request times out (after 'timeout' ms).
 * - onError (optional): a function that will be called if and when the request returns an error.
 *
 * Exactly one of onsuccess, ontimeout, and onerror will be called.
 * - onComplete (optional): a function that will be called when the request is over, whether successful, timeout, or
 *       error.
 */
function ajax(params) {
    if (!("url" in params))
        throw new Error("Missing url");
    if (!("method" in params))
        throw new Error("Missing method");
    const method = params.method ? params.method.toUpperCase() : undefined;
    if (method !== "GET" && method !== "POST")
        throw new Error("Missing or invalid method");

    const xhr = new XMLHttpRequest();
    xhr.open(method, params.url, true);
    const csrfToken = getCookie("csrftoken");

    if (csrfToken)
        xhr.setRequestHeader("X-CSRFToken", csrfToken);
    else
        console.warn("No CSRF cookie found!");

    if (params.contentType)
        xhr.setRequestHeader("Content-Type", params.contentType);

    const timeout = params.timeout || 5000;
    let completed = false;
    let timeoutToken = window.setTimeout(() => {
        if (!completed) {
            completed = true;
            if (params.onTimeout)
                params.onTimeout();
            if (params.onComplete)
                params.onComplete();
        }
    }, timeout);

    xhr.onreadystatechange = () => {
        if (xhr.readyState === XMLHttpRequest.DONE) {
            if (!completed) {
                completed = true;
                window.clearTimeout(timeoutToken);

                if (xhr.status === 0 || (xhr.status >= 200 && xhr.status < 400)) {
                    const response = xhr.responseText;
                    if (params.onSuccess)
                        params.onSuccess(response);
                } else if (params.onError)
                    params.onError();

                if (params.onComplete)
                    params.onComplete();
            }
        }
    };

    xhr.send(params.body);
}

function createElementWithClasses(tagName, ...classes) {
    const element = document.createElement(tagName);
    classes.forEach(c => element.classList.add(c));
    return element;
}

function findAncestor(node, predicate) {
    while (node && !predicate(node))
        node = node.parentNode;
    return node;
}

function removeAllChildren(element) {
    while (element.firstChild)
        element.removeChild(element.firstChild);
}

/*
 * Opens a file dialog to choose a file. If and when the user selects a file, onChoose is called with argument of the
 * selected file.
 *
 * This function is likely to be ignored by the browser unless called inside a user input event handler.
 */
function chooseFile(onFileChosen) {
    const fileInput = document.createElement("input");
    fileInput.setAttribute("type", "file");
    fileInput.addEventListener("change", () => {
        if (fileInput.files[0])
            onFileChosen(fileInput.files[0]);
    });

    fileInput.click();
}

let showModal = null;

(function() {
    const modalStack = [];

    function newModalElement(display, title, buttons) {
        const modal = createElementWithClasses("dialog", "modal");

        if (title !== undefined) {
            const titleElem = createElementWithClasses("div", "title");
            titleElem.innerText = title;
            modal.classList.add("with-title");
            modal.appendChild(titleElem);
        }

        const content = createElementWithClasses("div", "content");
        content.appendChild(display);
        modal.appendChild(content);

        const controls = createElementWithClasses("div", "controls");
        for (const buttonInfo of buttons) {
            const button = document.createElement("button");
            button.innerText = buttonInfo.text;
            if (buttonInfo.action)
                button.addEventListener("click", () => {
                    dismissModal();
                    buttonInfo.action();
                });
            else
                button.addEventListener("click", () => dismissModal());
            controls.appendChild(button);
        }
        modal.appendChild(controls);

        return modal;
    }

    function dismissModal() {
        if (modalStack) {
            const top = modalStack.pop();
            document.body.removeChild(top.element);
            document.body.removeChild(top.backdrop);
        }

        if (modalStack.length > 0)
            document.body.classList.add("modal-open");
        else
            document.body.classList.remove("modal-open");
    }

    function showModalImpl(display, params) {
        const title = params.title;
        const buttons = (params.buttons !== undefined) ? params.buttons : [{
            "text": "OK",
        }];

        const element = newModalElement(display, title, buttons);
        const backdrop = createElementWithClasses("div", "backdrop");
        const modal = {
            "element": element,
            "backdrop": backdrop
        };

        modalStack.push(modal);

        document.body.appendChild(backdrop);
        document.body.appendChild(element);
        document.body.classList.add("modal-open");
    }

    showModal = showModalImpl;
})();

function showModalMessage(text, params) {
    const p = document.createElement("p");
    p.innerText = text;
    showModal(p, params);
}

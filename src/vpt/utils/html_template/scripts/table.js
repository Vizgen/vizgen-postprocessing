// This script creates tooltips and clipboard buttons
// for the overflown values in the Input Parameters table's Value column
function createTooltip(tr) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    const title = document.createElement('p');
    title.className = 'tooltip__title';
    title.innerHTML = tr.children[0].innerHTML + ':';
    const text = document.createElement('p');
    text.className = 'tooltip__text';
    text.innerHTML = tr.children[1].innerHTML;
    tooltip.appendChild(title);
    tooltip.appendChild(text);

    return tooltip;
}

function createClipboardButton(content) {
    const button = document.createElement('button');
    button.className = 'clipboard-button';
    button.addEventListener('click', function () {
        navigator.clipboard.writeText(content);
    });
    button.setAttribute('style', 'margin: 0 0 0 4px; cursor: pointer; height: 24px;');
    const svg = new DOMParser()
        .parseFromString(
            '<svg class="clipboard-svg" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"> <path d="M15.75 15.7494H20.25V3.74939H8.25V8.24939" stroke="#727781" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/> <path d="M15.75 8.24951H3.75V20.2495H15.75V8.24951Z" stroke="#727781" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
            'image/svg+xml'
        )
        .querySelector('svg');
    button.appendChild(svg);

    return button;
}

function createCellText(content) {
    const text = document.createElement('div');
    text.setAttribute('style', 'white-space: nowrap; overflow: hidden; text-overflow: ellipsis;');
    text.append(content);

    return text;
}

const table = document.getElementsByClassName('dataframe')[0];
for (const tr of table.children[1].children) {
    const head = tr.children[0];
    const row = tr.children[1];
    const isOverflown = row.scrollWidth > row.clientWidth;
    if (isOverflown) {
        const content = row.innerHTML;
        const tooltip = createTooltip(tr);
        tr.appendChild(tooltip);
        tr.style.setProperty('position', 'relative');

        function mouseenter() {
            tooltip.style.display = 'block';
            row.style.display = 'flex';
            row.style.minWidth = '100%';
            row.innerHTML = '';
            row.appendChild(createCellText(content));
            row.appendChild(createClipboardButton(content));
        }

        function mouseleave() {
            tooltip.style.display = 'none';
            row.style.display = 'block';
            row.innerHTML = content;
        }

        tr.addEventListener('mouseenter', mouseenter);
        tr.addEventListener('mouseleave', mouseleave);
    }
}

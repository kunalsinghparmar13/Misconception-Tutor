class WorkspaceSwitch extends HTMLElement {
  connectedCallback() {
    const coding = this.getAttribute('current') === 'code';
    const choices = [
      ['tutor', 'Sikora AI', 'Learn, practise and explore', 'index.html?preview=header'],
      ['code', 'Humex', 'Talk with Humo, your 3D companion', 'code.html']
    ];
    const details = document.createElement('details');
    const summary = document.createElement('summary');
    const logo = this.firstElementChild || document.createElement('img');
    if (!this.firstElementChild) {
      logo.src = 'logo.png';
      logo.alt = 'Sikora AI';
    }
    summary.append(logo);
    summary.setAttribute('aria-label', 'Switch workspace: ' + (coding ? 'Humex' : 'Sikora AI'));
    details.append(summary);
    const menu = document.createElement('nav');
    menu.setAttribute('aria-label', 'Choose workspace');
    for (const [id, title, description, href] of choices) {
      const link = document.createElement('a');
      link.href = href;
      link.innerHTML = '<strong>' + title + '</strong><small>' + description + '</small>';
      if (id === (coding ? 'code' : 'tutor')) link.setAttribute('aria-current', 'page');
      menu.append(link);
    }
    details.append(menu);
    this.replaceChildren(details);
    document.addEventListener('pointerdown', event => {
      if (!this.contains(event.target)) details.open = false;
    });
    this.addEventListener('keydown', event => {
      if (event.key === 'Escape') { details.open = false; summary.focus(); }
    });
  }
}
customElements.define('workspace-switch', WorkspaceSwitch);

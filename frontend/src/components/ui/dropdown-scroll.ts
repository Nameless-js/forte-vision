/** Keep keyboard selection visible without scrolling the page or panel ancestors. */
export function revealDropdownOption(menu: HTMLElement, index: number) {
  const option = menu.querySelector<HTMLElement>(`[data-index="${index}"]`);
  if (!option) return;
  const top = option.offsetTop;
  const bottom = top + option.offsetHeight;
  if (top < menu.scrollTop) menu.scrollTop = top;
  else if (bottom > menu.scrollTop + menu.clientHeight) {
    menu.scrollTop = bottom - menu.clientHeight;
  }
}

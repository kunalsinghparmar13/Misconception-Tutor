self.onmessage = async ({data: code}) => {
  const lines = [];
  let size = 0;
  function append(line) {
    if (size >= 32000) return;
    const text = line.slice(0, 32000 - size);
    lines.push(text);
    size += text.length + 1;
  }
  try {
    importScripts('https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js');
    const python = await loadPyodide({stdout: append, stderr: append});
    await python.runPythonAsync(code);
  } catch (error) {
    append(String(error));
  }
  self.postMessage(lines.join('\n') || '(no output)');
};

function parseSGF(sgf) {
    let index = sgf.indexOf(';');
    const prefix = sgf.substr(0, index);
    sgf = sgf.substr(index + 1);
    index = sgf.indexOf(';');
    const header = sgf.substr(0, index);
    const moves = sgf.substr(index + 1);
    return [prefix, header, moves];
}

function parseHeader(headerStr) {
    const re = /([A-Z]{2})\[([^\[\]]*)\]/g;
    const header = {};
    let match;
    while (match = re.exec(headerStr)) {
        header[match[1]] = match[2];
    }
    return header;
}

function formatHeader(header) {
    const headerParts = Object.entries(header).map(([k, v]) => `${k}[${v}]`);
    return headerParts.join('');
}

function updateSGF(sgf, date){
  const [prefix, headerStr, moves] = parseSGF(sgf);
  const header = parseHeader(headerStr);
  header['PC'] = 'GOQUEST';
  header['TM'] = '180';
  header['OT'] = '2 fischer';
  header['C'] = '#OSR';
  header['DT'] = date;

  const newSGF = [prefix, formatHeader(header), moves].join(';');
  return newSGF;
}

// Exact evaluation of small arithmetic expressions (port of grounding.evaluate, which used Python's ast).
// Grammar follows Python precedence: + -  <  * /  <  unary + -  <  ** (right-associative).

import { Fraction } from './fraction';

export class UnsafeExpression extends Error {}

type Token = { kind: 'num' | 'name' | 'op'; value: string };

function tokenize(src: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;
  while (i < src.length) {
    const ch = src[i];
    if (/\s/.test(ch)) {
      i++;
      continue;
    }
    const num = /^(?:\d+(?:\.\d*)?|\.\d+)/.exec(src.slice(i));
    if (num) {
      tokens.push({ kind: 'num', value: num[0] });
      i += num[0].length;
      continue;
    }
    const name = /^[A-Za-z_]\w*/.exec(src.slice(i));
    if (name) {
      tokens.push({ kind: 'name', value: name[0] });
      i += name[0].length;
      continue;
    }
    if (src.startsWith('**', i)) {
      tokens.push({ kind: 'op', value: '**' });
      i += 2;
      continue;
    }
    if (src.startsWith('//', i)) throw new UnsafeExpression('operator not allowed');
    if ('+-*/()'.includes(ch)) {
      tokens.push({ kind: 'op', value: ch });
      i++;
      continue;
    }
    throw new UnsafeExpression(`not an arithmetic expression: unexpected '${ch}'`);
  }
  return tokens;
}

export function evaluate(expr: string, variables: Record<string, Fraction> = {}): Fraction {
  const tokens = tokenize(expr.trim());
  let pos = 0;
  const peek = (): Token | undefined => tokens[pos];
  const isOp = (v: string): boolean => {
    const t = peek();
    return !!t && t.kind === 'op' && t.value === v;
  };

  const check = (f: Fraction): Fraction => {
    if (f.num.toString(2).length > 4000) throw new UnsafeExpression('number too large');
    return f;
  };

  function parseExpr(): Fraction {
    let left = parseTerm();
    while (isOp('+') || isOp('-')) {
      const op = tokens[pos++].value;
      const right = parseTerm();
      left = check(op === '+' ? left.add(right) : left.sub(right));
    }
    return left;
  }

  function parseTerm(): Fraction {
    let left = parseUnary();
    while (isOp('*') || isOp('/')) {
      const op = tokens[pos++].value;
      const right = parseUnary();
      if (op === '/') {
        if (right.isZero()) throw new UnsafeExpression('division by zero');
        left = check(left.div(right));
      } else {
        left = check(left.mul(right));
      }
    }
    return left;
  }

  function parseUnary(): Fraction {
    if (isOp('+')) {
      pos++;
      return parseUnary();
    }
    if (isOp('-')) {
      pos++;
      return parseUnary().neg();
    }
    return parsePower();
  }

  function parsePower(): Fraction {
    const base = parseAtom();
    if (isOp('**')) {
      pos++;
      const exp = parseUnary();
      if (!exp.isInteger() || exp.abs().num > 12n || base.abs().sub(new Fraction(1000000n)).num > 0n) {
        throw new UnsafeExpression('exponent too large');
      }
      if (base.isZero() && exp.num < 0n) throw new UnsafeExpression('division by zero');
      return check(base.pow(Number(exp.num)));
    }
    return base;
  }

  function parseAtom(): Fraction {
    const t = peek();
    if (!t) throw new UnsafeExpression('not an arithmetic expression: unexpected end');
    if (t.kind === 'num') {
      pos++;
      return Fraction.fromDecimal(t.value);
    }
    if (t.kind === 'name') {
      pos++;
      if (t.value in variables) return variables[t.value];
      throw new UnsafeExpression(`unknown name '${t.value}'`);
    }
    if (t.value === '(') {
      pos++;
      const inner = parseExpr();
      if (!isOp(')')) throw new UnsafeExpression('not an arithmetic expression: missing )');
      pos++;
      return inner;
    }
    throw new UnsafeExpression('expression not allowed');
  }

  if (!tokens.length) throw new UnsafeExpression('not an arithmetic expression: empty');
  const value = parseExpr();
  if (pos !== tokens.length) throw new UnsafeExpression('not an arithmetic expression: trailing input');
  return value;
}

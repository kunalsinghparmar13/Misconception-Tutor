// Exact rational numbers (a port of Python's fractions.Fraction, just what the tutor needs).

function absBig(n: bigint): bigint {
  return n < 0n ? -n : n;
}

export function gcd(a: bigint, b: bigint): bigint {
  a = absBig(a);
  b = absBig(b);
  while (b !== 0n) {
    const t = a % b;
    a = b;
    b = t;
  }
  return a;
}

export function lcm(a: bigint, b: bigint): bigint {
  if (a === 0n || b === 0n) return 0n;
  return absBig(a * b) / gcd(a, b);
}

export class Fraction {
  readonly num: bigint;
  readonly den: bigint;

  constructor(num: bigint | number, den: bigint | number = 1n) {
    let n = BigInt(num);
    let d = BigInt(den);
    if (d === 0n) throw new RangeError('division by zero');
    if (d < 0n) {
      n = -n;
      d = -d;
    }
    const g = gcd(n, d) || 1n;
    this.num = n / g;
    this.den = d / g;
  }

  /** Exact value of a decimal string such as '-1.25' or '3'. */
  static fromDecimal(text: string): Fraction {
    const m = /^([+-]?)(\d*)(?:\.(\d*))?$/.exec(text.trim());
    if (!m || (!m[2] && !m[3])) throw new RangeError(`not a number: ${text}`);
    const sign = m[1] === '-' ? -1n : 1n;
    const intPart = m[2] || '0';
    const frac = m[3] || '';
    const num = BigInt(intPart + frac) * sign;
    const den = 10n ** BigInt(frac.length);
    return new Fraction(num, den);
  }

  add(o: Fraction): Fraction {
    return new Fraction(this.num * o.den + o.num * this.den, this.den * o.den);
  }

  sub(o: Fraction): Fraction {
    return new Fraction(this.num * o.den - o.num * this.den, this.den * o.den);
  }

  mul(o: Fraction): Fraction {
    return new Fraction(this.num * o.num, this.den * o.den);
  }

  div(o: Fraction): Fraction {
    if (o.num === 0n) throw new RangeError('division by zero');
    return new Fraction(this.num * o.den, this.den * o.num);
  }

  neg(): Fraction {
    return new Fraction(-this.num, this.den);
  }

  pow(exp: number): Fraction {
    let result = new Fraction(1n);
    const base: Fraction = exp < 0 ? new Fraction(1n).div(this) : this;
    for (let i = 0; i < Math.abs(exp); i++) result = result.mul(base);
    return result;
  }

  equals(o: Fraction): boolean {
    return this.num === o.num && this.den === o.den;
  }

  isZero(): boolean {
    return this.num === 0n;
  }

  isInteger(): boolean {
    return this.den === 1n;
  }

  abs(): Fraction {
    return new Fraction(absBig(this.num), this.den);
  }

  /** Closest fraction with denominator <= maxDen (Python's limit_denominator). */
  limitDenominator(maxDen = 1000000n): Fraction {
    if (this.den <= maxDen) return this;
    let p0 = 0n;
    let q0 = 1n;
    let p1 = 1n;
    let q1 = 0n;
    let n = this.num;
    let d = this.den;
    for (;;) {
      const a = n / d;
      const q2 = q0 + a * q1;
      if (q2 > maxDen) break;
      [p0, q0, p1, q1] = [p1, q1, p0 + a * p1, q2];
      [n, d] = [d, n - a * d];
    }
    const k = (maxDen - q0) / q1;
    const bound1 = new Fraction(p0 + k * p1, q0 + k * q1);
    const bound2 = new Fraction(p1, q1);
    const diff1 = bound1.sub(this).abs();
    const diff2 = bound2.sub(this).abs();
    return diff2.sub(diff1).num <= 0n ? bound2 : bound1;
  }

  toString(): string {
    return this.den === 1n ? this.num.toString() : `${this.num}/${this.den}`;
  }
}

export function fmt(value: Fraction): string {
  return value.toString();
}

import React from 'react';

interface FractionDisplayProps {
  numerator: number | string;
  denominator: number | string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

export const FractionDisplay: React.FC<FractionDisplayProps> = ({
  numerator,
  denominator,
  size = 'md',
  className = '',
}) => {
  const sizeClasses = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-2xl',
    xl: 'text-4xl',
  };

  const lineHeights = {
    sm: 'border-b-[1.5px]',
    md: 'border-b-2',
    lg: 'border-b-[2.5px]',
    xl: 'border-b-3',
  };

  const paddingY = {
    sm: 'py-0.5 px-1',
    md: 'py-0.5 px-1.5',
    lg: 'py-1 px-2',
    xl: 'py-1.5 px-3',
  };

  return (
    <span
      className={`inline-flex flex-col items-center justify-center align-middle font-mono font-medium ${sizeClasses[size]} ${className}`}
      style={{ verticalAlign: 'middle' }}
    >
      <span className={`w-full text-center ${lineHeights[size]} border-current ${paddingY[size]}`}>
        {numerator}
      </span>
      <span className={`w-full text-center ${paddingY[size]}`}>
        {denominator}
      </span>
    </span>
  );
};

interface MathExpressionProps {
  firstOperand: { num: number; den: number };
  operator: '+' | '-' | '×' | '÷';
  secondOperand: { num: number; den: number };
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

export const MathExpression: React.FC<MathExpressionProps> = ({
  firstOperand,
  operator,
  secondOperand,
  size = 'xl',
  className = '',
}) => {
  const operatorSpacing = {
    sm: 'mx-2 text-base',
    md: 'mx-3 text-lg',
    lg: 'mx-4 text-2xl',
    xl: 'mx-6 text-4xl',
  };

  return (
    <div className={`inline-flex items-center justify-center font-mono ${className}`}>
      <FractionDisplay
        numerator={firstOperand.num}
        denominator={firstOperand.den}
        size={size}
      />
      <span className={`text-[#A3B5A0] font-semibold ${operatorSpacing[size]}`}>
        {operator}
      </span>
      <FractionDisplay
        numerator={secondOperand.num}
        denominator={secondOperand.den}
        size={size}
      />
    </div>
  );
};

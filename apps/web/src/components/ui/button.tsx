import type { ButtonHTMLAttributes, ReactNode } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'text' | 'danger'

export function buttonClass(variant: ButtonVariant = 'primary', className = '') {
  return `btn btn-${variant} ${className}`.trim()
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  children: ReactNode
}

export function Button({ variant = 'primary', className = '', type = 'button', children, ...props }: ButtonProps) {
  return <button type={type} className={buttonClass(variant, className)} {...props}>{children}</button>
}

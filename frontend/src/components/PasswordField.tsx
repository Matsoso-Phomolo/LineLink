import { useState } from "react";

type PasswordFieldProps = {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete?: string;
  minLength?: number;
  required?: boolean;
};

export function PasswordField({
  id,
  value,
  onChange,
  autoComplete,
  minLength,
  required
}: PasswordFieldProps) {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <div className="password-field">
      <input
        id={id}
        required={required}
        minLength={minLength}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        type={isVisible ? "text" : "password"}
        autoComplete={autoComplete}
      />

      <button
        type="button"
        className="password-eye-button"
        aria-label={isVisible ? "Hide password" : "Show password"}
        title={isVisible ? "Hide password" : "Show password"}
        onClick={() => setIsVisible((current) => !current)}
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" focusable="false">
          <path d="M12 5c5 0 8.5 4.3 9.5 7-1 2.7-4.5 7-9.5 7s-8.5-4.3-9.5-7C3.5 9.3 7 5 12 5Zm0 2C8.6 7 6 9.5 4.7 12 6 14.5 8.6 17 12 17s6-2.5 7.3-5C18 9.5 15.4 7 12 7Zm0 2.2a2.8 2.8 0 1 1 0 5.6 2.8 2.8 0 0 1 0-5.6Z" />
        </svg>
      </button>
    </div>
  );
}

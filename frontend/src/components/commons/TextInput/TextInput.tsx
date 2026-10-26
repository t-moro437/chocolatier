import { ChangeEvent, KeyboardEvent, useState } from 'react';
import styles from './TextInput.module.css';

type TextInputProps = {
  type?: string;
  value: string;
  onChange?: (event: ChangeEvent<HTMLInputElement>) => void; // ← イベントごと渡す
  onChangeText?: (text: string) => void; // ← テキストだけ欲しい場合
  onKeyDown?: (event: KeyboardEvent<HTMLInputElement>)=> void;
  placeholder?: string;
};

function TextInput({ type = 'text', value, onChange, onChangeText, onKeyDown, placeholder }: TextInputProps) {
  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    onChange?.(e);             // イベントをそのまま渡す
    onChangeText?.(e.target.value); // テキストだけ返す

  };

  return (
    <input
      className={styles.TextInputClass}
      type={type}
      name="text"
      value={value}
      onChange={handleChange}
      onKeyDown={onKeyDown}
      placeholder={placeholder}
    />
  );
}

export default TextInput;

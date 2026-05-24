import { useMemo, useState } from "react";

type HeroPhotoCarouselProps = {
  title: string;
  folder: "villages" | "nul-campus" | "lines";
  filenames: string[];
};

export function HeroPhotoCarousel({ title, folder, filenames }: HeroPhotoCarouselProps) {
  const [index, setIndex] = useState(0);
  const images = useMemo(() => filenames.map((name) => `/hero/${folder}/${name}`), [filenames, folder]);
  const current = images[index % images.length];

  return (
    <button
      className="hero-photo-slot"
      type="button"
      onClick={() => setIndex((value) => (value + 1) % images.length)}
      style={{ backgroundImage: `linear-gradient(rgba(8, 31, 28, 0.36), rgba(8, 31, 28, 0.68)), url("${current}")` }}
    >
      <span>{title}</span>
      <small>{index + 1}/{images.length}</small>
    </button>
  );
}

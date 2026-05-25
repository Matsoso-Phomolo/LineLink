import { useEffect, useMemo, useState } from "react";

type HeroPhotoCarouselProps = {
  title: string;
  folder: "villages" | "nul-campus" | "lines";
  filenames: string[];
};

type HeroManifest = Partial<Record<HeroPhotoCarouselProps["folder"], string[]>>;

export function HeroPhotoCarousel({ title, folder, filenames }: HeroPhotoCarouselProps) {
  const [index, setIndex] = useState(0);
  const [manifestImages, setManifestImages] = useState<string[] | null>(null);
  const imageNames = manifestImages?.length ? manifestImages : filenames;
  const images = useMemo(() => imageNames.map((name) => `/hero/${folder}/${name}`), [imageNames, folder]);
  const current = images[index % images.length];

  useEffect(() => {
    let isMounted = true;
    fetch(`/hero/manifest.json?v=${Date.now()}`, { cache: "no-store" })
      .then((response) => (response.ok ? response.json() as Promise<HeroManifest> : null))
      .then((manifest) => {
        const folderImages = manifest?.[folder]?.filter(Boolean) ?? [];
        if (isMounted && folderImages.length) {
          setManifestImages(folderImages);
          setIndex(0);
        }
      })
      .catch(() => {
        if (isMounted) setManifestImages(null);
      });
    return () => {
      isMounted = false;
    };
  }, [folder]);

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

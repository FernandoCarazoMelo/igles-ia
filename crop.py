from PIL import Image


def crop_to_square(input_path, output_path):
    img = Image.open(input_path)
    x, y = img.size

    # Tomamos el lado más corto como referencia
    min_side = min(x, y)

    # Calculamos coordenadas de recorte centrado
    left = (x - min_side) // 2
    top = (y - min_side) // 2
    right = left + min_side
    bottom = top + min_side

    # Recortar
    img_cropped = img.crop((left, top, right, bottom))

    # Redimensionar a 3000x3000 (requisito Apple)
    img_resized = img_cropped.resize((3000, 3000), Image.LANCZOS)

    # Guardar
    img_resized.save(output_path, format="PNG", quality=95)


if __name__ == "__main__":
    crop_to_square("pope.png", "papa-leon-xiv-square.png")

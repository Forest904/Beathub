Icon assets

- Put your `.svg` files in this folder.
- In Create React App you can import an SVG as a React component:

  - Example: `import { ReactComponent as MyIcon } from '../assets/icons/my-icon.svg';`
  - Usage: `<MyIcon className="w-6 h-6" />`

- You can also import the file URL directly:

  - `import downloadUrl from '../assets/icons/download.svg';`
  - `<img src={downloadUrl} alt="Download" />`

- Tailwind sizing works on the wrapper via `w-* h-*` classes when used as a component.


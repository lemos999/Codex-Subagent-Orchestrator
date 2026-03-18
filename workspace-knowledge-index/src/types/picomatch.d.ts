declare module 'picomatch' {
  type Matcher = (input: string) => boolean;

  interface Options {
    dot?: boolean;
    windows?: boolean;
    contains?: boolean;
    matchBase?: boolean;
    [key: string]: unknown;
  }

  function picomatch(
    glob: string | string[],
    options?: Options,
  ): Matcher;

  export default picomatch;
}

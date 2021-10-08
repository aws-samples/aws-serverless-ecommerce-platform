module.exports = {
  "roots": [
    "<rootDir>/tests/lint/"
  ],
  testMatch: [ '**/*.test.ts'],
  "transform": {
    "^.+\\.tsx?$": "ts-jest"
  },
};

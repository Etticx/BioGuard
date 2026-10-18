export class SessionExpired extends Error {}
export class RequestError extends Error {constructor(message:string,public status:number){super(message);}}

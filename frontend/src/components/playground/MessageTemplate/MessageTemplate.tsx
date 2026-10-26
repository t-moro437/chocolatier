import Message from "../../commons/Message/Message";

function MessageTemplate() {
  return (
    <div>
      <div>
        <h2>Message</h2>
        <Message message ="warningメッセージ" mode="warning"/>
        <Message message ="infoメッセージ" mode="info" duration={3000}/>
        <Message message ="Errorメッセージ" mode="error"/>
      </div>
      <div>
        <h3>size（省略すると medium）</h3>
        <Message message ="smallメッセージ" mode="info" size="small"/>
        <Message message ="mediumメッセージ" mode="info" size="medium"/>
        <Message message ="largeメッセージ" mode="info" size="large"/>
      </div>
    </div>
  );
}

export default MessageTemplate;
